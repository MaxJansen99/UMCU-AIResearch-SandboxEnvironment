import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.services.query_service import QueryService


class QueryServer:
    def __init__(self, query_service: QueryService, frontend_dir: Path) -> None:
        self.query_service = query_service
        self.frontend_dir = frontend_dir

    def handler(self) -> type[BaseHTTPRequestHandler]:
        query_service = self.query_service
        frontend_dir = self.frontend_dir

        class QueryHTTPRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                # GET / and /health: backend health check.
                if self.path in {"/", "/health"}:
                    self._send_json({"ok": True, "service": "dicom-query", "pacs_url": query_service.orthanc.base_url})
                    return

                # GET /dashboard: serve the React dashboard entry HTML.
                if self.path == "/dashboard":
                    self._send_file(frontend_dir / "index.html")
                    return

                # GET /assets/...: serve built frontend JS, CSS, images and other static assets.
                if self.path.startswith("/assets/"):
                    requested = self.path.removeprefix("/assets/").split("?", 1)[0]
                    self._send_file(frontend_dir / "assets" / requested)
                    return

                self._send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                # POST /query: run metadata filters against Orthanc and return stats/results.
                if self.path != "/query":
                    self._send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)
                    return

                try:
                    payload = self._read_json_body()
                    response = query_service.run(payload)
                    self._send_json(response)
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

            def _read_json_body(self) -> dict[str, Any]:
                content_length = self.headers.get("Content-Length", "0")
                body_size = int(content_length)
                raw_body = self.rfile.read(body_size)
                payload = json.loads(raw_body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("Request body must be a JSON object.")
                return payload

            def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
                response = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def _send_file(self, path: Path) -> None:
                if not path.is_file():
                    self._send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)
                    return

                content = path.read_bytes()
                content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            def log_message(self, format: str, *args: Any) -> None:
                print(f"{self.address_string()} - {format % args}")

        return QueryHTTPRequestHandler

    def build(self, host: str, port: int) -> ThreadingHTTPServer:
        return ThreadingHTTPServer((host, port), self.handler())
