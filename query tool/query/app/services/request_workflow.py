from typing import Any

from app.repositories.exports_repository import ExportsRepository
from app.repositories.requests_repository import RequestsRepository
from app.services.database import Database
from app.services.export_service import ExportService
from app.services.orthanc_client import OrthancClient


class WorkflowError(Exception):
    pass


class NotFoundError(WorkflowError):
    pass


class InvalidStateError(WorkflowError):
    pass


class ForbiddenMutationError(WorkflowError):
    pass


class RequestWorkflowService:
    def __init__(
        self,
        database: Database,
        orthanc: OrthancClient | None = None,
        export_service: ExportService | None = None,
        requests_repository: RequestsRepository | None = None,
        exports_repository: ExportsRepository | None = None,
    ) -> None:
        self.database = database
        self.orthanc = orthanc
        self.export_service = export_service
        self.requests_repository = requests_repository or RequestsRepository()
        self.exports_repository = exports_repository or ExportsRepository()

    def create_request(self, user: dict[str, Any], title: str, filters_json: dict[str, Any] | None) -> dict[str, Any]:
        with self.database.connect() as conn:
            request_id = self.requests_repository.create_request(conn, int(user["id"]), title, filters_json)
            conn.commit()

        return self.get_request(request_id)

    def add_items(self, request_id: int, user: dict[str, Any], orthanc_study_ids: list[str]) -> dict[str, Any]:
        if not orthanc_study_ids:
            raise ValueError("'orthanc_study_id' or 'orthanc_study_ids' is required.")

        request = self.get_request(request_id)
        self._ensure_owner(request, user)
        self._ensure_status(request, "DRAFT")

        with self.database.connect() as conn:
            self.requests_repository.add_items(conn, request_id, orthanc_study_ids)
            conn.commit()

        return self.get_request(request_id)

    def submit(self, request_id: int, user: dict[str, Any]) -> dict[str, Any]:
        request = self.get_request(request_id)
        self._ensure_owner(request, user)
        self._ensure_status(request, "DRAFT")

        with self.database.connect() as conn:
            self.requests_repository.update_status(conn, request_id, "SUBMITTED")
            conn.commit()

        return self.get_request(request_id)

    def list_mine(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            requests = self.requests_repository.list_by_creator(conn, int(user["id"]))
        return self._hydrate_requests(requests)

    def list_pending(self) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            requests = self.requests_repository.list_pending(conn)
        return self._hydrate_requests(requests)

    def decide(
        self,
        request_id: int,
        user: dict[str, Any],
        decision: str,
        reason: str | None,
    ) -> dict[str, Any]:
        normalized_decision = normalize_decision(decision)
        if normalized_decision == "REJECTED" and not (reason or "").strip():
            raise ValueError("'reason' is required when rejecting a request.")

        request = self.get_request(request_id)
        self._ensure_status(request, "SUBMITTED")

        with self.database.connect() as conn:
            self.requests_repository.add_approval(conn, request_id, int(user["id"]), normalized_decision, reason)
            self.requests_repository.update_status(conn, request_id, normalized_decision)
            conn.commit()

        updated_request = self.get_request(request_id)
        if normalized_decision == "APPROVED" and self.export_service is not None:
            export = self.export_service.prepare_approved_export(updated_request, user)
            updated_request["export"] = export

        return updated_request

    def get_request(self, request_id: int) -> dict[str, Any]:
        with self.database.connect() as conn:
            request = self.requests_repository.get_request(conn, request_id)
            if request is None:
                raise NotFoundError("Request not found.")
            return self._hydrate_request(conn, request)

    def _study_info(self, orthanc_study_id: str) -> dict[str, Any] | None:
        if self.orthanc is None:
            return None

        try:
            study = self.orthanc.get_study(orthanc_study_id)
        except Exception:
            return None

        tags = study.get("MainDicomTags", {})
        series_ids = study.get("Series", [])
        modalities: set[str] = set()
        for series_id in series_ids:
            try:
                series = self.orthanc.get_series(series_id)
            except Exception:
                continue
            modality = series.get("MainDicomTags", {}).get("Modality")
            if modality:
                modalities.add(str(modality))

        return {
            "study_date": tags.get("StudyDate", ""),
            "study_description": tags.get("StudyDescription", ""),
            "modalities": sorted(modalities),
        }

    def _hydrate_requests(self, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            return [self._hydrate_request(conn, request) for request in requests]

    def _hydrate_request(self, conn: Any, request: dict[str, Any]) -> dict[str, Any]:
        items = self.requests_repository.list_items(conn, int(request["id"]))
        request["items"] = [
            {
                **item,
                "study_info": self._study_info(item["orthanc_study_id"]),
            }
            for item in items
        ]
        request["approval"] = self.requests_repository.latest_approval(conn, int(request["id"]))
        request["export"] = self.exports_repository.find_by_request_id(conn, int(request["id"]))
        return request

    def _ensure_owner(self, request: dict[str, Any], user: dict[str, Any]) -> None:
        if request["created_by_user_id"] != user["id"]:
            raise ForbiddenMutationError("Researchers can only mutate their own requests.")

    def _ensure_status(self, request: dict[str, Any], expected_status: str) -> None:
        if request["status"] != expected_status:
            raise InvalidStateError(f"Request must be {expected_status}, current status is {request['status']}.")

def normalize_decision(decision: str) -> str:
    normalized = decision.strip().upper()
    if normalized == "APPROVE":
        return "APPROVED"
    if normalized == "REJECT":
        return "REJECTED"
    if normalized in {"APPROVED", "REJECTED"}:
        return normalized
    raise ValueError("'decision' must be APPROVE, REJECT, APPROVED, or REJECTED.")
