import argparse
import hashlib
import json
import os
import re
import smtplib
import ssl
import time
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copy2
from typing import Any, Dict, List, Optional, Tuple

import requests


SAFE_PATH_RE = re.compile(r"[^A-Za-z0-9_.-]+")
REQUEST_ID_KEYS = ("instance_ids", "uids", "ids", "requested_ids")


def safe_path_component(value: str) -> str:
    value = value.strip()
    if not value:
        return "item"
    return SAFE_PATH_RE.sub("_", value)


def send_email(to_email: str, subject: str, body: str) -> None:
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_user or not smtp_password:
        print("SMTP credentials not configured, skipping email.")
        return

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as exc:
        print(f"Failed to send email: {exc}")


def load_records(records_file: Path) -> List[Dict[str, Any]]:
    if records_file.exists():
        with records_file.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_records(records_file: Path, records: List[Dict[str, Any]]) -> None:
    records_file.parent.mkdir(parents=True, exist_ok=True)
    with records_file.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def add_record(records_file: Path, record: Dict[str, Any]) -> None:
    records = load_records(records_file)
    records.append(record)
    save_records(records_file, records)


def update_record(records_file: Path, request_hash: str, updates: Dict[str, Any]) -> bool:
    records = load_records(records_file)
    changed = False
    for record in records:
        if record.get("request_hash") == request_hash:
            record.update(updates)
            changed = True
    if changed:
        save_records(records_file, records)
    return changed


def find_record(records_file: Path, request_hash: str) -> Optional[Dict[str, Any]]:
    for record in load_records(records_file):
        if record.get("request_hash") == request_hash:
            return record
    return None


def compute_request_hash(instance_ids: List[str]) -> str:
    normalized = "\n".join(sorted(instance_ids))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def resolve_instance_id(pacs_url: str, auth: Optional[Tuple[str, str]], identifier: str) -> Optional[str]:
    identifier = identifier.strip()
    if not identifier:
        return None

    direct_url = f"{pacs_url.rstrip('/')}/instances/{identifier}"
    resp = requests.get(direct_url, auth=auth, timeout=30)
    if resp.status_code == 200:
        return identifier

    query = {"Level": "Instance", "Query": {"SOPInstanceUID": identifier}}
    resp = requests.post(f"{pacs_url.rstrip('/')}/tools/find", auth=auth, json=query, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0]
    return None


def fetch_instance_file(
    pacs_url: str,
    auth: Optional[Tuple[str, str]],
    instance_id: str,
    destination: Path,
) -> None:
    url = f"{pacs_url.rstrip('/')}/instances/{instance_id}/file"
    response = requests.get(url, auth=auth, stream=True, timeout=60)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def make_hardlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    try:
        os.link(source, target)
    except OSError:
        print(f"Hardlink failed, copied file instead: {source} -> {target}")
        copy2(source, target)


def extract_request_ids(payload: Dict[str, Any]) -> List[str]:
    for key in REQUEST_ID_KEYS:
        if key in payload:
            ids = payload[key]
            if isinstance(ids, list) and all(isinstance(item, str) for item in ids):
                return ids
            break
    raise ValueError("Request body must contain a list of strings under 'instance_ids', 'uids', 'ids', or 'requested_ids'.")


class DatamanagerRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/", "/health"}:
            self._send_json({"ok": True, "service": "dicom-datamanager"})
            return
        if self.path.startswith("/requests"):
            records_file = Path(self.server.records_file)
            records = load_records(records_file)

            # Parse query parameters
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # Filter by status if provided
            status_filter = query_params.get("status", [None])[0]
            if status_filter:
                valid_statuses = {"pending", "accepted", "rejected", "failed"}
                if status_filter not in valid_statuses:
                    self._send_json({
                        "ok": False,
                        "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                    }, status=HTTPStatus.BAD_REQUEST)
                    return
                records = [r for r in records if r.get("status") == status_filter]

            self._send_json({"ok": True, "requests": records})
            return
        self._send_json({"ok": False, "error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/review":
            self.handle_new_request()
            return
        if self.path == "/review/decision":
            self.handle_decision()
            return
        self._send_json({"ok": False, "error": "Not found."}, status=HTTPStatus.NOT_FOUND)

    def handle_new_request(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            user_id = payload.get("userID")
            if not isinstance(user_id, str) or not user_id:
                raise ValueError("Request must include a non-empty 'userID'.")
            ids = extract_request_ids(payload)
            request_hash = compute_request_hash(ids)

            # Check if this request hash has been accepted before
            records_file = Path(self.server.records_file)
            existing_accepted = None
            for record in load_records(records_file):
                if record.get("request_hash") == request_hash and record.get("status") == "accepted":
                    existing_accepted = record
                    break

            if existing_accepted:
                # Automatically accept this request since it was approved before
                record = {
                    "user_id": user_id,
                    "request_hash": request_hash,
                    "requested_images": ids,
                    "status": "accepted",
                    "created_at": time.time(),
                    "processed_by": "auto-approved",
                    "decision_message": "Automatically approved - previously accepted request",
                    "processed_at": time.time(),
                    "instances": existing_accepted.get("instances"),
                    "request_folder": existing_accepted.get("request_folder"),
                }
                add_record(records_file, record)

                # Create hardlinks for the new request
                depersonalized_root = Path(self.server.depersonalized_root)
                request_folder = depersonalized_root / "requests" / request_hash
                request_folder.mkdir(parents=True, exist_ok=True)

                instances = existing_accepted.get("instances", [])
                for instance in instances:
                    stored_file = Path(instance["stored_file"])
                    link_target = request_folder / stored_file.name
                    make_hardlink(stored_file, link_target)

                email_body = f"Your request {request_hash} has been automatically accepted.\n\nThis request was previously approved and has been processed.\n\nRequest folder:\n{request_folder}\n\nProcessed instances:\n{json.dumps(instances, indent=2)}"
                send_email(user_id, "DICOM Review Request Auto-Approved", email_body)

                self._send_json({
                    "ok": True,
                    "message": "Request automatically approved - previously accepted.",
                    "request_hash": request_hash,
                    "status": "accepted",
                    "instances": instances
                })
                return

            # Create new pending request
            record = {
                "user_id": user_id,
                "request_hash": request_hash,
                "requested_images": ids,
                "status": "pending",
                "created_at": time.time(),
                "processed_by": None,
                "decision_message": None,
                "processed_at": None,
                "instances": None,
            }
            add_record(records_file, record)
            self._send_json({"ok": True, "message": "Request received and pending review.", "request_hash": request_hash})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def handle_decision(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            request_hash = payload.get("request_hash")
            decision = payload.get("decision")
            message = payload.get("message", "")
            processed_by = payload.get("processed_by", "datamanager")

            if not isinstance(request_hash, str) or not request_hash:
                raise ValueError("Request must include 'request_hash'.")
            if decision not in {"accept", "reject"}:
                raise ValueError("Decision must be 'accept' or 'reject'.")
            if not isinstance(message, str):
                raise ValueError("Message must be a string.")

            records_file = Path(self.server.records_file)
            record = find_record(records_file, request_hash)
            if record is None:
                raise ValueError(f"Request not found: {request_hash}")
            if record.get("status") != "pending":
                raise ValueError(f"Request is already {record.get('status')}.")

            if decision == "reject":
                # Apply decision to all pending requests with the same hash
                records = load_records(records_file)
                updated_count = 0
                for rec in records:
                    if rec.get("request_hash") == request_hash and rec.get("status") == "pending":
                        update_record(records_file, request_hash, {
                            "status": "rejected",
                            "processed_by": processed_by,
                            "decision_message": message,
                            "processed_at": time.time(),
                        })
                        send_email(rec["user_id"], "DICOM Review Request Rejected", f"Your request {request_hash} was rejected.\n\nMessage:\n{message}")
                        updated_count += 1

                self._send_json({"ok": True, "status": "rejected", "updated_requests": updated_count})
                return

            # Accept decision - apply to all pending requests with the same hash
            records = load_records(records_file)
            pending_requests = [rec for rec in records if rec.get("request_hash") == request_hash and rec.get("status") == "pending"]

            if not pending_requests:
                raise ValueError(f"No pending requests found for hash: {request_hash}")

            # Process the first request to get the instances data
            result = self._process_accept(pending_requests[0], message, processed_by)

            # Apply the same result to all other pending requests with the same hash
            instances = result.get("instances", [])
            request_folder = result.get("request_folder", "")
            processed_at = time.time()

            for rec in pending_requests[1:]:  # Skip the first one already processed
                update_record(records_file, rec["request_hash"], {
                    "status": "accepted",
                    "processed_by": processed_by,
                    "decision_message": message,
                    "processed_at": processed_at,
                    "instances": instances,
                    "request_folder": request_folder,
                })

                # Create hardlinks for this request
                depersonalized_root = Path(self.server.depersonalized_root)
                req_folder = depersonalized_root / "requests" / request_hash
                req_folder.mkdir(parents=True, exist_ok=True)

                for instance in instances:
                    stored_file = Path(instance["stored_file"])
                    link_target = req_folder / stored_file.name
                    make_hardlink(stored_file, link_target)

                email_body = f"Your request {request_hash} has been accepted.\n\nMessage:\n{message}\n\nRequest folder:\n{req_folder}\n\nProcessed instances:\n{json.dumps(instances, indent=2)}"
                send_email(rec["user_id"], "DICOM Review Request Accepted", email_body)

            result["updated_requests"] = len(pending_requests)
            self._send_json(result)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _process_accept(self, record: Dict[str, Any], message: str, processed_by: str) -> Dict[str, Any]:
        user_id = record["user_id"]
        request_hash = record["request_hash"]
        ids = record["requested_images"]
        depersonalized_root = Path(self.server.depersonalized_root)
        auth = self.server.auth
        pacs_url = self.server.pacs_url

        instance_store = depersonalized_root / "instances"
        request_folder = depersonalized_root / "requests" / request_hash
        request_folder.mkdir(parents=True, exist_ok=True)

        resolved_ids: List[str] = []
        unresolved: List[str] = []
        for identifier in ids:
            instance_id = resolve_instance_id(pacs_url, auth, identifier)
            if instance_id is None:
                unresolved.append(identifier)
            else:
                resolved_ids.append(instance_id)

        if unresolved:
            error_msg = f"Could not resolve identifiers: {unresolved}"
            update_record(Path(self.server.records_file), request_hash, {
                "status": "failed",
                "processed_by": processed_by,
                "decision_message": message,
                "processed_at": time.time(),
                "error": error_msg,
            })
            send_email(user_id, "DICOM Review Request Failed", f"Your request {request_hash} failed.\n\n{error_msg}\n\nMessage:\n{message}")
            return {"ok": False, "error": error_msg}

        instances: List[Dict[str, Any]] = []
        for instance_id in sorted(set(resolved_ids)):
            stored_file = instance_store / f"{safe_path_component(instance_id)}.dcm"
            if not stored_file.exists():
                try:
                    fetch_instance_file(pacs_url, auth, instance_id, stored_file)
                except Exception as exc:
                    error_msg = f"Failed to fetch instance {instance_id}: {exc}"
                    update_record(Path(self.server.records_file), request_hash, {
                        "status": "failed",
                        "processed_by": processed_by,
                        "decision_message": message,
                        "processed_at": time.time(),
                        "error": error_msg,
                    })
                    send_email(user_id, "DICOM Review Request Failed", f"Your request {request_hash} failed.\n\n{error_msg}\n\nMessage:\n{message}")
                    return {"ok": False, "error": error_msg}

            link_target = request_folder / f"{safe_path_component(instance_id)}.dcm"
            make_hardlink(stored_file, link_target)
            instances.append({
                "instance_id": instance_id,
                "stored_file": str(stored_file),
                "linked_file": str(link_target),
            })

        update_record(Path(self.server.records_file), request_hash, {
            "status": "accepted",
            "processed_by": processed_by,
            "decision_message": message,
            "processed_at": time.time(),
            "instances": instances,
            "request_folder": str(request_folder),
        })

        email_body = f"Your request {request_hash} has been accepted.\n\nMessage:\n{message}\n\nRequest folder:\n{request_folder}\n\nProcessed instances:\n{json.dumps(instances, indent=2)}"
        send_email(user_id, "DICOM Review Request Accepted", email_body)
        return {"ok": True, "status": "accepted", "request_hash": request_hash, "instances": instances}

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        content_length = self.headers.get("Content-Length", "0")
        try:
            body_size = int(content_length)
        except ValueError:
            self._send_json({"ok": False, "error": "Invalid Content-Length header."}, status=HTTPStatus.BAD_REQUEST)
            return None

        raw_body = self.rfile.read(body_size)
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            return payload
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return None

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


class DatamanagerHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, RequestHandlerClass, pacs_url, auth, depersonalized_root, records_file):
        super().__init__(server_address, RequestHandlerClass)
        self.pacs_url = pacs_url
        self.auth = auth
        self.depersonalized_root = depersonalized_root
        self.records_file = records_file


def create_ssl_context(certfile: str, keyfile: str, ca_file: Optional[str] = None) -> ssl.SSLContext:
    if not os.path.isfile(certfile) or not os.path.isfile(keyfile):
        raise FileNotFoundError(f"TLS certificate or key file not found: {certfile}, {keyfile}")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    if ca_file:
        if not os.path.isfile(ca_file):
            raise FileNotFoundError(f"TLS CA file not found: {ca_file}")
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=ca_file)
    return context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the DICOM datamanager HTTP service.")
    parser.add_argument("pacs_url", nargs="?", help="PACS base URL (e.g. http://orthanc:8042).")
    parser.add_argument("--host", default=os.environ.get("DATAMANAGER_HOST", "0.0.0.0"), help="Host interface.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DATAMANAGER_PORT", "8001")), help="Port to listen on.")
    parser.add_argument("--tls", action="store_true", default=os.environ.get("DATAMANAGER_TLS", "false").lower() in ("1", "true", "yes"), help="Enable TLS.")
    parser.add_argument("--tls-cert", default=os.environ.get("DATAMANAGER_TLS_CERT", "/certs/server.crt"), help="TLS certificate path.")
    parser.add_argument("--tls-key", default=os.environ.get("DATAMANAGER_TLS_KEY", "/certs/server.key"), help="TLS key path.")
    parser.add_argument("--tls-ca", default=os.environ.get("DATAMANAGER_TLS_CA", ""), help="TLS CA bundle path.")
    parser.add_argument("--records-file", default=os.environ.get("RECORDS_FILE", "/depersonalized/records.json"), help="Path to records JSON file.")
    parser.add_argument("--depersonalized-root", default=os.environ.get("DEPERSONALIZED_ROOT", "/depersonalized"), help="Root path for depersonalized storage.")
    return parser.parse_args()


def run_server(
    pacs_url: str,
    auth: Optional[Tuple[str, str]],
    host: str,
    port: int,
    tls: bool,
    tls_cert: str,
    tls_key: str,
    tls_ca: Optional[str],
    depersonalized_root: str,
    records_file: str,
) -> None:
    server = DatamanagerHTTPServer((host, port), DatamanagerRequestHandler, pacs_url, auth, depersonalized_root, records_file)
    protocol = "http"
    if tls:
        context = create_ssl_context(tls_cert, tls_key, tls_ca or None)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        protocol = "https"

    print(f"DICOM datamanager listening on {protocol}://{host}:{port}")
    print(f"PACS URL: {pacs_url}")
    print(f"Depersonalized root: {depersonalized_root}")
    print(f"Records file: {records_file}")
    server.serve_forever()


if __name__ == "__main__":
    args = parse_args()
    pacs_url = os.environ.get("DATAMANAGER_PACS_URL") or args.pacs_url
    if not pacs_url:
        raise RuntimeError("PACS URL must be provided via DATAMANAGER_PACS_URL or the first positional argument.")
    pacs_user = os.environ.get("DATAMANAGER_PACS_USER", "orthanc")
    pacs_password = os.environ.get("DATAMANAGER_PACS_PASSWORD", "orthanc")
    auth = (pacs_user, pacs_password) if pacs_user and pacs_password else None

    run_server(
        pacs_url=pacs_url,
        auth=auth,
        host=args.host,
        port=args.port,
        tls=args.tls,
        tls_cert=args.tls_cert,
        tls_key=args.tls_key,
        tls_ca=args.tls_ca if args.tls_ca else None,
        depersonalized_root=args.depersonalized_root,
        records_file=args.records_file,
    )