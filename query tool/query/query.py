import argparse
import json
import os
import ssl
import threading
import time
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import requests

# Type aliases
FilterOp = Callable[[Any, Any], bool]
FilterSpec = Tuple[str, str, Any]  # (tag_name, operator, value)
StatsSummary = Dict[str, Dict[str, int]]


# --------- Filter operators --------- #

def op_eq(a, b): return a == b
def op_neq(a, b): return a != b
def op_gt(a, b): return a is not None and b is not None and a > b
def op_gte(a, b): return a is not None and b is not None and a >= b
def op_lt(a, b): return a is not None and b is not None and a < b
def op_lte(a, b): return a is not None and b is not None and a <= b
def op_contains(a, b): return a is not None and b is not None and str(b) in str(a)
def op_startswith(a, b): return a is not None and b is not None and str(a).startswith(str(b))
def op_endswith(a, b): return a is not None and b is not None and str(a).endswith(str(b))
def op_in(a, b): return a is not None and b is not None and a in b
def op_not_in(a, b): return a is not None and b is not None and a not in b
def op_is_none(a, _): return a is None
def op_not_none(a, _): return a is not None


OPERATORS: Dict[str, FilterOp] = {
    "==": op_eq,
    "!=": op_neq,
    ">": op_gt,
    ">=": op_gte,
    "<": op_lt,
    "<=": op_lte,
    "contains": op_contains,
    "startswith": op_startswith,
    "endswith": op_endswith,
    "in": op_in,
    "not in": op_not_in,
    "is None": op_is_none,
    "not None": op_not_none,
}

blacklist_tags = {""}
unnecissary_tags = {"SOPInstanceUID", "InstanceNumber", "CodingSchemeIdentificationSequence", "ContributingEquipmentSequence", "DimensionOrganizationSequence", 
                              "DimensionIndexSequence", "NumberOfFrames", "ImagePositionPatient", "PixelSpacing", "TotalPixelMatrixOriginSequence", "OpticalPathSequence", 
                              "OpticalPathSequence", "SpecimenDescriptionSequence", "SharedFunctionalGroupsSequence", "PerFrameFunctionalGroupsSequence"}
depersanalization_tags = {"PatientIdentityRemoved", "DeidentificationMethod", "DeidentificationMethodCodeSequence", "ImageOrientationPatient"}

dont_use_tags = blacklist_tags | unnecissary_tags | depersanalization_tags

def _stats_key(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def summarize_stats(stats_counters: Dict[str, Counter]) -> StatsSummary:
    return {tag: dict(counter.most_common()) for tag, counter in stats_counters.items()}


# --------- Main filtering function --------- #
def collect_all_tag_stats(pacs_url: str, auth: Optional[Tuple[str, str]] = None) -> Tuple[StatsSummary, int, int]:
    """
    Collect stats on all DICOM tags from PACS.
    Returns stats summary, total series, total instances.
    """
    stats_counters: Dict[str, Counter] = {}
    total_series = 0
    total_instances = 0

    # Get all series IDs (no filters)
    query_body = {"Level": "Series", "Query": {}}
    resp = requests.post(
        f"{pacs_url.rstrip('/')}/tools/find",
        auth=auth,
        json=query_body,
        timeout=30,
    )
    resp.raise_for_status()
    series_ids = resp.json() if isinstance(resp.json(), list) else []

    for series_id in series_ids:
        total_series += 1
        try:
            # Fetch series metadata
            series_resp = requests.get(
                f"{pacs_url.rstrip('/')}/series/{series_id}", auth=auth, timeout=30
            )
            if series_resp.status_code != 200:
                print(f"Warning: Failed to fetch metadata for series {series_id}")
                continue
            series_meta = series_resp.json()

            # Collect series-level tags
            for tag, value in series_meta.get("MainDicomTags", {}).items():
                if tag not in stats_counters:
                    stats_counters[tag] = Counter()
                stats_counters[tag][_stats_key(value)] += 1

            # Get instances in series
            instances_resp = requests.get(
                f"{pacs_url.rstrip('/')}/series/{series_id}/instances", auth=auth, timeout=30
            )
            if instances_resp.status_code == 200:
                instances = instances_resp.json()
                for instance_id in instances:
                    if isinstance(instance_id, dict) and "ID" in instance_id:
                        instance_id = instance_id["ID"]
                    else:                        
                        print(f"Warning: Unexpected instance format in series {series_id}: {instance_id}")
                        continue
                    total_instances += 1
                    # Fetch instance tags
                    tags_resp = requests.get(
                        f"{pacs_url.rstrip('/')}/instances/{instance_id}/tags", auth=auth, timeout=30
                    )

                    if tags_resp.status_code == 200:
                        instance_tags = tags_resp.json()
                        # Normalize Orthanc tag structure (e.g. {'0008,0060': {...}}) to Name->Value mapping
                        normalized_instance_tags = normalize_orthanc_dicom_tags(instance_tags)
                        # Collect instance-level stats
                        for tag, value in normalized_instance_tags.items():
                            if tag in dont_use_tags:
                                continue
                            if tag not in stats_counters:
                                stats_counters[tag] = Counter()
                            stats_counters[tag][_stats_key(value)] += 1
        except Exception:
            continue

    return summarize_stats(stats_counters), total_series, total_instances


def collect_and_save_stats(pacs_url: str, auth: Optional[Tuple[str, str]], stats_file: str = "stats.json"):
    """
    Collect all tag stats from PACS and save to a JSON file.
    """
    print("Collecting DICOM header stats from PACS...")
    start_time = perf_counter()
    stats, total_series, total_instances = collect_all_tag_stats(pacs_url, auth)
    elapsed = perf_counter() - start_time
    data = {
        "stats": stats,
        "total_series": total_series,
        "total_instances": total_instances,
        "elapsed_seconds": elapsed,
        "timestamp": time.time(),
    }
    with open(stats_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Stats collected and saved to {stats_file} in {elapsed:.2f}s")


def periodic_stats_collection(pacs_url: str, auth: Optional[Tuple[str, str]], interval_hours: int = 24):
    """
    Run stats collection periodically from PACS.
    """
    while True:
        time.sleep(interval_hours * 3600)
        collect_and_save_stats(pacs_url, auth)


def normalize_filter_specs(raw_filters: Iterable[Iterable[Any]]) -> List[FilterSpec]:
    """
    Validate and normalize incoming filters into (tag, operator, value) tuples.
    """
    normalized: List[FilterSpec] = []
    for raw_filter in raw_filters:
        if not isinstance(raw_filter, (list, tuple)) or len(raw_filter) != 3:
            raise ValueError(
                "Each filter must be a list or tuple with exactly 3 items: "
                "[tag_name, operator, value]."
            )

        name, op_str, expected = raw_filter
        if not isinstance(name, str) or not name:
            raise ValueError("Filter tag_name must be a non-empty string.")
        if not isinstance(op_str, str) or op_str not in OPERATORS:
            raise ValueError(
                f"Unsupported operator: {op_str}. "
                f"Supported operators: {sorted(OPERATORS)}"
            )
        normalized.append((name, op_str, expected))
    return normalized


def run_query_request(
    payload: Dict[str, Any],
    pacs_url: str,
    pacs_user: Optional[str] = None,
    pacs_password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a single query payload and return a JSON-serializable response.
    """
    raw_filters = payload.get("filters", [])
    if not isinstance(raw_filters, list):
        raise ValueError("'filters' must be a list.")

    filter_specs = normalize_filter_specs(raw_filters)

    stats_tags = payload.get("stats_tags", [])
    if not isinstance(stats_tags, list) or not all(isinstance(tag, str) for tag in stats_tags):
        raise ValueError("'stats_tags' must be a list of strings.")

    auth = None
    if pacs_user and pacs_password:
        auth = (pacs_user, pacs_password)

    start_time = perf_counter()
    response = pacs_query(
        pacs_url=pacs_url,
        auth=auth,
        filter_specs=filter_specs,
        stats_tags=stats_tags,
    )
    response["elapsed_seconds"] = perf_counter() - start_time
    return response


def normalize_orthanc_dicom_tags(dicom_tags: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Orthanc per-tag format into a simple Name->Value mapping, recursively."""
    if not isinstance(dicom_tags, dict):
        return {}

    normalized: Dict[str, Any] = {}
    for tag_key, entry in dicom_tags.items():
        if isinstance(entry, dict):
            name = entry.get("Name")
            value = entry.get("Value")
            if name is not None:
                normalized_value = normalize_orthanc_value(value)
                normalized[name] = normalized_value
            else:
                # If no Name, treat as nested dict and normalize recursively
                normalized[tag_key] = normalize_orthanc_dicom_tags(entry)
        else:
            normalized[tag_key] = entry

    return normalized


def normalize_orthanc_value(value: Any) -> Any:
    """Recursively normalize nested Orthanc values (dicts or lists of dicts)."""
    if isinstance(value, dict):
        return normalize_orthanc_dicom_tags(value)
    elif isinstance(value, list):
        return [normalize_orthanc_value(item) for item in value]
    else:
        return value


def pacs_safe_get(meta: Dict[str, Any], key: str) -> Any:
    # Orthanc metadata is in MainDicomTags for most standard tags.
    tags = meta.get("MainDicomTags", {})
    if key in tags:
        return tags[key]
    # fallback for top-level items
    return meta.get(key)


def pacs_safe_get_full(meta: Dict[str, Any], key: str) -> Any:
    """
    Get tag from full DICOM metadata, including tags not in MainDicomTags.
    This requires fetching the full series metadata.
    """
    # First check MainDicomTags
    tags = meta.get("MainDicomTags", {})
    if key in tags:
        return tags[key]

    # Check if we have full DICOM tags (from /series/{id}/tags endpoint or normalized map)
    dicom_tags = meta.get("DicomTags", {})
    if isinstance(dicom_tags, dict):
        # If already normalized to Name->Value map
        if key in dicom_tags:
            return dicom_tags[key]

        # If in Orthanc raw format tag->dict map, resolve by Name field
        for entry in dicom_tags.values():
            if isinstance(entry, dict) and entry.get("Name") == key:
                return entry.get("Value")

    # fallback for top-level items
    return meta.get(key)


def pacs_item_matches(meta: Dict[str, Any], filter_specs: List[FilterSpec]) -> bool:
    for name, op_str, expected in filter_specs:
        op = OPERATORS.get(op_str)
        if op is None:
            raise ValueError(f"Unsupported operator: {op_str}")
        actual = pacs_safe_get_full(meta, name)
        if not op(actual, expected):
            return False
    return True


def pacs_query(
    pacs_url: str,
    auth: Optional[Tuple[str, str]],
    filter_specs: List[FilterSpec],
    stats_tags: List[str],
) -> Dict[str, Any]:
    # Get total files/instances in PACS for diagnostics.
    total_instances = 0
    try:
        stats_resp = requests.get(
            f"{pacs_url.rstrip('/')}/statistics", auth=auth, timeout=30
        )
        if stats_resp.status_code == 200:
            total_instances = stats_resp.json().get("CountInstances", 0)
    except Exception:
        pass

    filter_specs = [spec for spec in filter_specs if spec[0] not in dont_use_tags]
    stats_tags = [tag for tag in stats_tags if tag not in dont_use_tags]

    # Build an Orthanc find query using equality filters if available.
    query_body: Dict[str, Any] = {"Level": "Series", "Query": {}}

    for name, op_str, expected in filter_specs:
        if op_str != "==":
            # Non-equality is not pushed to PACS; we'll filter after metadata pull.
            continue
        query_body["Query"][name] = expected

    resp = requests.post(
        f"{pacs_url.rstrip('/')}/tools/find",
        auth=auth,
        json=query_body,
        timeout=30,
    )
    resp.raise_for_status()
    ids = resp.json() if isinstance(resp.json(), list) else []

    matched: List[Dict[str, Any]] = []
    stats_counters: Dict[str, Counter] = {tag: Counter() for tag in stats_tags}

    for resource_id in ids:
        # Fetch series metadata; fallback to instance if needed.
        series = requests.get(
            f"{pacs_url.rstrip('/')}/series/{resource_id}", auth=auth, timeout=30
        )
        if series.status_code != 200:
            continue
        meta = series.json()

        if not pacs_item_matches(meta, filter_specs):
            continue

        matched.append({"id": resource_id, "meta": meta})

        # Collect series-level stats
        for tag in stats_tags:
            value = pacs_safe_get(meta, tag)
            if value is not None:
                stats_counters[tag][_stats_key(value)] += 1

        # Collect stats from instances in this series, with instance-level filtering
        try:
            instances_resp = requests.get(
                f"{pacs_url.rstrip('/')}/series/{resource_id}/instances",
                auth=auth,
                timeout=30,
            )
            if instances_resp.status_code == 200:
                instances = instances_resp.json()
                print(f"Series {resource_id} has {len(instances)} instances")
                print(instances[0] if instances else "No instances found")
                for instance in instances:
                    if isinstance(instance, dict) and "ID" in instance:
                        instance_id = instance["ID"]
                    else:
                        print(f"Warning: Unexpected instance format: {instance}")
                        continue
                    print(f"Processing instance {instance_id}")
                    # Fetch instance tags
                    instance_resp = requests.get(
                        f"{pacs_url.rstrip('/')}/instances/{instance_id}/tags",
                        auth=auth,
                        timeout=30,
                    )
                    print(f"Instance tags fetch status: {instance_resp.status_code}")
                    if instance_resp.status_code == 200:
                        instance_tags = instance_resp.json()
                        # Normalize Orthanc tag structure (e.g. {'0008,0060': {...}}) to Name->Value mapping
                        normalized_instance_tags = normalize_orthanc_dicom_tags(instance_tags)
                        # Check filters on instance level
                        print(f"Instance {instance_id} tags: {normalized_instance_tags}")
                        instance_meta = {
                            "MainDicomTags": meta.get('MainDicomTags', {}),
                            "DicomTags": normalized_instance_tags,
                        }
                        if not pacs_item_matches(instance_meta, filter_specs):
                            print(f"Instance {instance_id} does not match filters, skipping stats collection")
                            continue
                        # Collect instance-level stats
                        for tag in stats_tags:
                            value = pacs_safe_get_full(instance_meta, tag)
                            print(f"Value for tag {tag} in instance {instance_id}: {value}")
                            if value is not None:
                                print(f"Collecting {tag}: {value}")
                                stats_counters[tag][_stats_key(value)] += 1
        except Exception:
            # If instance fetching fails, continue with series-level stats only
            pass

    return {
        "ok": True,
        "root": pacs_url,
        "pacs": True,
        "filters": filter_specs,
        "total_instances_in_pacs": total_instances,
        "total_series_found": len(ids),
        "match_count": len(matched),
        "matches": [match["id"] for match in matched],  # Just IDs, not full metadata
        "stats": summarize_stats(stats_counters),
    }


def create_ssl_context(certfile: str, keyfile: str, ca_file: Optional[str] = None) -> ssl.SSLContext:
    if not os.path.isfile(certfile) or not os.path.isfile(keyfile):
        raise FileNotFoundError(
            f"TLS certificate or key file not found: {certfile}, {keyfile}"
        )

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)

    if ca_file:
        if not os.path.isfile(ca_file):
            raise FileNotFoundError(f"TLS CA file not found: {ca_file}")
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=ca_file)

    return context


def build_handler(pacs_url: str, pacs_user: Optional[str], pacs_password: Optional[str]):
    class QueryHTTPRequestHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
            response = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def do_GET(self) -> None:
            if self.path in {"/", "/health"}:
                self._send_json(
                    {
                        "ok": True,
                        "service": "dicom-query",
                        "pacs_url": pacs_url,
                    }
                )
                return

            self._send_json(
                {"ok": False, "error": "Not found."},
                status=HTTPStatus.NOT_FOUND,
            )

        def do_POST(self) -> None:
            if self.path != "/query":
                self._send_json(
                    {"ok": False, "error": "Not found."},
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            content_length = self.headers.get("Content-Length", "0")
            try:
                body_size = int(content_length)
            except ValueError:
                self._send_json(
                    {"ok": False, "error": "Invalid Content-Length header."},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            raw_body = self.rfile.read(body_size)
            try:
                payload = json.loads(raw_body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("Request body must be a JSON object.")
                response = run_query_request(
                    payload,
                    pacs_url=pacs_url,
                    pacs_user=pacs_user,
                    pacs_password=pacs_password,
                )
                self._send_json(response, status=HTTPStatus.OK)
            except Exception as exc:
                self._send_json(
                    {"ok": False, "error": str(exc)},
                    status=HTTPStatus.BAD_REQUEST,
                )

        def log_message(self, format: str, *args: Any) -> None:
            # Keep container logs concise but useful.
            print(f"{self.address_string()} - {format % args}")

    return QueryHTTPRequestHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DICOM query HTTP service.")
    parser.add_argument(
        "pacs_url",
        help="PACS base URL (e.g. http://orthanc:8042).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("QUERY_HOST", "0.0.0.0"),
        help="Host interface to bind to. Defaults to QUERY_HOST or 0.0.0.0.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("QUERY_PORT", "8000")),
        help="Port to listen on. Defaults to QUERY_PORT or 8000.",
    )
    parser.add_argument(
        "--tls",
        action="store_true",
        default=os.environ.get("QUERY_TLS", "false").lower() in ("1", "true", "yes"),
        help="Enable TLS/HTTPS. Can also be set with QUERY_TLS=1/true/yes.",
    )
    parser.add_argument(
        "--tls-cert",
        default=os.environ.get("QUERY_TLS_CERT", "/certs/server.crt"),
        help="Path to TLS certificate file.",
    )
    parser.add_argument(
        "--tls-key",
        default=os.environ.get("QUERY_TLS_KEY", "/certs/server.key"),
        help="Path to TLS private key file.",
    )
    parser.add_argument(
        "--tls-ca",
        default=os.environ.get("QUERY_TLS_CA", ""),
        help="Path to CA bundle for client cert verification (optional).",
    )
    return parser.parse_args()


def serve_http(
    pacs_url: str,
    pacs_user: Optional[str],
    pacs_password: Optional[str],
    host: str,
    port: int,
    tls: bool = False,
    tls_cert: Optional[str] = None,
    tls_key: Optional[str] = None,
    tls_ca: Optional[str] = None,
) -> None:
    server = ThreadingHTTPServer((host, port), build_handler(pacs_url, pacs_user, pacs_password))

    protocol = "http"
    if tls:
        context = create_ssl_context(tls_cert or "/certs/server.crt", tls_key or "/certs/server.key", tls_ca or None)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        protocol = "https"

    print(f"DICOM query service listening on {protocol}://{host}:{port}")
    print(f"PACS URL: {pacs_url}")
    server.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    pacs_url = args.pacs_url
    pacs_user = os.environ.get("QUERY_PACS_USER", "orthanc")
    pacs_password = os.environ.get("QUERY_PACS_PASSWORD", "orthanc")
    auth = (pacs_user, pacs_password) if pacs_user and pacs_password else None
    
    # Collect initial stats
    collect_and_save_stats(pacs_url, auth)
    
    # Start periodic stats collection in a background thread
    stats_thread = threading.Thread(target=periodic_stats_collection, args=(pacs_url, auth), daemon=True)
    stats_thread.start()
    
    serve_http(
        pacs_url=pacs_url,
        pacs_user=pacs_user,
        pacs_password=pacs_password,
        host=args.host,
        port=args.port,
        tls=args.tls,
        tls_cert=args.tls_cert,
        tls_key=args.tls_key,
        tls_ca=args.tls_ca if args.tls_ca else None,
    )
