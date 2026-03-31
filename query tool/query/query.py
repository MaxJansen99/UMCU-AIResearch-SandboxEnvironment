import argparse
import json
import os
import ssl
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pydicom
from pydicom import dcmread

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


# --------- Core helpers --------- #

def safe_get(ds: pydicom.dataset.Dataset, key: str) -> Any:
    """
    Get a tag by keyword; return None if missing.
    Example keys: 'Modality', 'PatientID', 'SliceThickness'.
    """
    return getattr(ds, key, None)


def build_specific_tags(
    filter_specs: List[FilterSpec],
    extra_tags: Optional[Iterable[str]] = None,
) -> List[str]:
    """
    Build list of tags to ask pydicom to read, based on filters + extra tags.
    """
    tags = {name for (name, _, _) in filter_specs if name}
    if extra_tags:
        tags.update(extra_tags)
    return list(tags)


def _stats_key(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def summarize_stats(stats_counters: Dict[str, Counter]) -> StatsSummary:
    return {tag: dict(counter.most_common()) for tag, counter in stats_counters.items()}


def file_matches(ds: pydicom.dataset.Dataset, filter_specs: List[FilterSpec]) -> bool:
    """
    Return True if dataset matches all filter conditions.
    Missing tags are passed to operators as None.
    """
    for name, op_str, expected in filter_specs:
        op = OPERATORS.get(op_str)
        if op is None:
            raise ValueError(f"Unsupported operator: {op_str}")
        actual = safe_get(ds, name)
        if not op(actual, expected):
            return False
    return True


# --------- Main filtering function --------- #

def filter_dicom_files(
    root: str,
    filter_specs: List[FilterSpec],
    recursive: bool = True,
    extra_tags_to_read: Optional[Iterable[str]] = None,
    stats_tags_to_collect: Optional[Iterable[str]] = None,
) -> Tuple[List[str], int, int, StatsSummary]:
    """
    Walk `root`, evaluate filters on DICOM headers, and return:
      - list of matching file paths
      - total number of files visited (all extensions)
      - number of files successfully read as DICOM
      - optional stats distributions for matched files
    """
    stats_tags = list(dict.fromkeys(stats_tags_to_collect or []))
    specific_tags = build_specific_tags(filter_specs, [*(extra_tags_to_read or []), *stats_tags])

    matched: List[str] = []
    total_files = 0
    dicom_files = 0
    stats_counters: Dict[str, Counter] = {tag: Counter() for tag in stats_tags}

    def paths() -> Iterable[str]:
        if recursive:
            for dirpath, _, filenames in os.walk(root):
                for fname in filenames:
                    yield os.path.join(dirpath, fname)
        else:
            for fname in os.listdir(root):
                full = os.path.join(root, fname)
                if os.path.isfile(full):
                    yield full

    for path in paths():
        total_files += 1
        try:
            ds = dcmread(
                path,
                stop_before_pixels=True,
                specific_tags=specific_tags or None,
            )
            dicom_files += 1
        except Exception:
            continue

        try:
            if file_matches(ds, filter_specs):
                matched.append(path)
                for tag in stats_tags:
                    stats_counters[tag][_stats_key(safe_get(ds, tag))] += 1
        except Exception:
            continue

    return matched, total_files, dicom_files, summarize_stats(stats_counters)


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


def run_query_request(payload: Dict[str, Any], default_root: str) -> Dict[str, Any]:
    """
    Execute a single query payload and return a JSON-serializable response.
    """
    raw_filters = payload.get("filters", [])
    if not isinstance(raw_filters, list):
        raise ValueError("'filters' must be a list.")

    filter_specs = normalize_filter_specs(raw_filters)

    root = payload.get("root", default_root)
    if not isinstance(root, str) or not root:
        raise ValueError("'root' must be a non-empty string.")

    recursive = payload.get("recursive", True)
    if not isinstance(recursive, bool):
        raise ValueError("'recursive' must be a boolean.")

    stats_tags = payload.get("stats_tags", [])
    if not isinstance(stats_tags, list) or not all(isinstance(tag, str) for tag in stats_tags):
        raise ValueError("'stats_tags' must be a list of strings.")

    extra_tags = payload.get("extra_tags", [])
    if not isinstance(extra_tags, list) or not all(isinstance(tag, str) for tag in extra_tags):
        raise ValueError("'extra_tags' must be a list of strings.")

    start_time = perf_counter()
    matches, total_files, dicom_files, stats = filter_dicom_files(
        root=root,
        filter_specs=filter_specs,
        recursive=recursive,
        extra_tags_to_read=extra_tags,
        stats_tags_to_collect=stats_tags,
    )
    elapsed_seconds = perf_counter() - start_time

    return {
        "ok": True,
        "root": root,
        "recursive": recursive,
        "filters": filter_specs,
        "total_files": total_files,
        "dicom_files": dicom_files,
        "match_count": len(matches),
        "matches": matches,
        "stats": stats,
        "elapsed_seconds": elapsed_seconds,
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


def build_handler(default_root: str):
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
                        "default_root": default_root,
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
                response = run_query_request(payload, default_root=default_root)
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
        "root",
        nargs="?",
        default=None,
        help="Path to the DICOM root directory. Defaults to DICOM_ROOT or idc-data/.",
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
    default_root: str,
    host: str,
    port: int,
    tls: bool = False,
    tls_cert: Optional[str] = None,
    tls_key: Optional[str] = None,
    tls_ca: Optional[str] = None,
) -> None:
    server = ThreadingHTTPServer((host, port), build_handler(default_root))

    protocol = "http"
    if tls:
        context = create_ssl_context(tls_cert or "/certs/server.crt", tls_key or "/certs/server.key", tls_ca or None)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        protocol = "https"

    print(f"DICOM query service listening on {protocol}://{host}:{port}")
    print(f"Default root: {default_root}")
    server.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    dicom_root = args.root or os.environ.get("DICOM_ROOT", "idc-data/")
    serve_http(
        default_root=dicom_root,
        host=args.host,
        port=args.port,
        tls=args.tls,
        tls_cert=args.tls_cert,
        tls_key=args.tls_key,
        tls_ca=args.tls_ca if args.tls_ca else None,
    )
