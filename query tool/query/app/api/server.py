import json
import mimetypes
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.services.auth import AuthService, AuthenticationError, AuthorizationError, public_user
from app.services.database import Database
from app.services.query_service import QueryService
from app.services.request_workflow import (
    ForbiddenMutationError,
    InvalidStateError,
    NotFoundError,
    RequestWorkflowService,
)


class QueryServer:
    def __init__(
        self,
        query_service: QueryService,
        frontend_dir: Path,
        database: Database,
        auth_service: AuthService,
        request_workflow: RequestWorkflowService,
    ) -> None:
        self.query_service = query_service
        self.frontend_dir = frontend_dir
        self.database = database
        self.auth_service = auth_service
        self.request_workflow = request_workflow

    def handler(self) -> type[BaseHTTPRequestHandler]:
        query_service = self.query_service
        frontend_dir = self.frontend_dir
        database = self.database
        auth_service = self.auth_service
        request_workflow = self.request_workflow

        class QueryHTTPRequestHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                path = self._path()

                # GET / and /health: backend health check.
                if path in {"/", "/health"}:
                    self._send_json({"ok": True, "service": "dicom-query", "pacs_url": query_service.orthanc.base_url})
                    return

                # GET /health/db: verify the backend can connect to Postgres.
                if path == "/health/db":
                    try:
                        self._send_json(database.health())
                    except Exception as exc:
                        self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)
                    return

                # GET /auth/me: return the user attached to the bearer token.
                if path == "/auth/me":
                    try:
                        user = self._current_user()
                        self._send_json({"ok": True, "user": public_user(user)})
                    except AuthenticationError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                    return

                if path == "/requests/mine":
                    try:
                        user = self._require_role("researcher")
                        self._send_json({"ok": True, "requests": request_workflow.list_mine(user)})
                    except Exception as exc:
                        self._send_workflow_error(exc)
                    return

                if path == "/requests/pending":
                    try:
                        self._require_role("datamanager")
                        self._send_json({"ok": True, "requests": request_workflow.list_pending()})
                    except Exception as exc:
                        self._send_workflow_error(exc)
                    return

                # Serve the React app entry for client-side routes.
                if path in {"/", "/dashboard", "/login", "/researcher", "/datamanager"}:
                    self._send_file(frontend_dir / "index.html")
                    return

                # GET /assets/...: serve built frontend JS, CSS, images and other static assets.
                if path.startswith("/assets/"):
                    requested = path.removeprefix("/assets/")
                    self._send_file(frontend_dir / "assets" / requested)
                    return

                self._send_json({"ok": False, "error": "Not found."}, HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                path = self._path()

                # POST /auth/login: exchange demo credentials for an in-memory bearer token.
                if path == "/auth/login":
                    try:
                        payload = self._read_json_body()
                        username = self._required_string(payload, "username")
                        password = self._required_string(payload, "password")
                        self._send_json({"ok": True, **auth_service.login(username, password)})
                    except AuthenticationError as exc:
                        self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                    except Exception as exc:
                        self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return

                if path == "/requests":
                    try:
                        user = self._require_role("researcher")
                        payload = self._read_json_body()
                        title = self._required_string(payload, "title")
                        filters_json = self._optional_dict(payload, "filters_json")
                        request = request_workflow.create_request(user, title, filters_json)
                        self._send_json({"ok": True, "request": request}, HTTPStatus.CREATED)
                    except Exception as exc:
                        self._send_workflow_error(exc)
                    return

                items_match = re.fullmatch(r"/requests/(\d+)/items", path)
                if items_match:
                    try:
                        user = self._require_role("researcher")
                        payload = self._read_json_body()
                        study_ids = self._study_ids(payload)
                        request = request_workflow.add_items(int(items_match.group(1)), user, study_ids)
                        self._send_json({"ok": True, "request": request})
                    except Exception as exc:
                        self._send_workflow_error(exc)
                    return

                submit_match = re.fullmatch(r"/requests/(\d+)/submit", path)
                if submit_match:
                    try:
                        user = self._require_role("researcher")
                        request = request_workflow.submit(int(submit_match.group(1)), user)
                        self._send_json({"ok": True, "request": request})
                    except Exception as exc:
                        self._send_workflow_error(exc)
                    return

                decision_match = re.fullmatch(r"/requests/(\d+)/decision", path)
                if decision_match:
                    try:
                        user = self._require_role("datamanager")
                        payload = self._read_json_body()
                        decision = self._required_string(payload, "decision")
                        reason = self._optional_string(payload, "reason")
                        request = request_workflow.decide(int(decision_match.group(1)), user, decision, reason)
                        self._send_json({"ok": True, "request": request})
                    except Exception as exc:
                        self._send_workflow_error(exc)
                    return

                # POST /query: run metadata filters against Orthanc and return stats/results.
                if path != "/query":
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

            def _path(self) -> str:
                return urlparse(self.path).path

            def _required_string(self, payload: dict[str, Any], key: str) -> str:
                value = payload.get(key)
                if not isinstance(value, str) or not value:
                    raise ValueError(f"'{key}' is required.")
                return value

            def _optional_string(self, payload: dict[str, Any], key: str) -> str | None:
                value = payload.get(key)
                if value is None:
                    return None
                if not isinstance(value, str):
                    raise ValueError(f"'{key}' must be a string.")
                return value

            def _optional_dict(self, payload: dict[str, Any], key: str) -> dict[str, Any] | None:
                value = payload.get(key)
                if value is None:
                    return None
                if not isinstance(value, dict):
                    raise ValueError(f"'{key}' must be an object.")
                return value

            def _study_ids(self, payload: dict[str, Any]) -> list[str]:
                single_study_id = payload.get("orthanc_study_id")
                if isinstance(single_study_id, str) and single_study_id:
                    return [single_study_id]

                study_ids = payload.get("orthanc_study_ids")
                if isinstance(study_ids, list) and all(isinstance(item, str) and item for item in study_ids):
                    return study_ids

                raise ValueError("'orthanc_study_id' must be a string or 'orthanc_study_ids' must be a string array.")

            def _current_user(self) -> dict[str, Any]:
                return auth_service.authenticate(self.headers.get("Authorization"))

            def _require_role(self, role: str) -> dict[str, Any]:
                try:
                    return auth_service.require_role(role, self._current_user())
                except AuthorizationError:
                    raise

            def _send_workflow_error(self, exc: Exception) -> None:
                if isinstance(exc, AuthenticationError):
                    self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.UNAUTHORIZED)
                    return
                if isinstance(exc, (AuthorizationError, ForbiddenMutationError)):
                    self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.FORBIDDEN)
                    return
                if isinstance(exc, NotFoundError):
                    self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
                    return
                if isinstance(exc, (InvalidStateError, ValueError)):
                    self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

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
