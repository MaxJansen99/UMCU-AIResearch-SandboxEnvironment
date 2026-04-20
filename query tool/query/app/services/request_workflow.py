from typing import Any

from psycopg.types.json import Jsonb

from app.services.database import Database
from app.services.export_service import ExportService, export_from_row
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
    ) -> None:
        self.database = database
        self.orthanc = orthanc
        self.export_service = export_service

    def create_request(self, user: dict[str, Any], title: str, filters_json: dict[str, Any] | None) -> dict[str, Any]:
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO selection_requests (created_by_user_id, title, status, filters_json)
                    VALUES (%s, %s, 'DRAFT', %s)
                    RETURNING id
                    """,
                    (user["id"], title, Jsonb(filters_json or {})),
                )
                request_id = cur.fetchone()[0]
                conn.commit()

        return self.get_request(request_id)

    def add_items(self, request_id: int, user: dict[str, Any], orthanc_study_ids: list[str]) -> dict[str, Any]:
        if not orthanc_study_ids:
            raise ValueError("'orthanc_study_id' or 'orthanc_study_ids' is required.")

        request = self.get_request(request_id)
        self._ensure_owner(request, user)
        self._ensure_status(request, "DRAFT")

        with self.database.connect() as conn:
            with conn.cursor() as cur:
                for orthanc_study_id in orthanc_study_ids:
                    cur.execute(
                        """
                        INSERT INTO selection_items (request_id, orthanc_study_id)
                        VALUES (%s, %s)
                        """,
                        (request_id, orthanc_study_id),
                    )
                conn.commit()

        return self.get_request(request_id)

    def submit(self, request_id: int, user: dict[str, Any]) -> dict[str, Any]:
        request = self.get_request(request_id)
        self._ensure_owner(request, user)
        self._ensure_status(request, "DRAFT")

        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE selection_requests
                    SET status = 'SUBMITTED'
                    WHERE id = %s
                    """,
                    (request_id,),
                )
                conn.commit()

        return self.get_request(request_id)

    def list_mine(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        return self._list_requests(
            """
            SELECT id, created_by_user_id, title, status, filters_json, created_at
            FROM selection_requests
            WHERE created_by_user_id = %s
            ORDER BY created_at DESC, id DESC
            """,
            (user["id"],),
        )

    def list_pending(self) -> list[dict[str, Any]]:
        return self._list_requests(
            """
            SELECT id, created_by_user_id, title, status, filters_json, created_at
            FROM selection_requests
            WHERE status = 'SUBMITTED'
            ORDER BY created_at ASC, id ASC
            """,
            (),
        )

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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO approvals (request_id, decided_by_user_id, decision, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (request_id, user["id"], normalized_decision, reason),
                )
                cur.execute(
                    """
                    UPDATE selection_requests
                    SET status = %s
                    WHERE id = %s
                    """,
                    (normalized_decision, request_id),
                )
                conn.commit()

        updated_request = self.get_request(request_id)
        if normalized_decision == "APPROVED" and self.export_service is not None:
            export = self.export_service.prepare_approved_export(updated_request, user)
            updated_request["export"] = export

        return updated_request

    def get_request(self, request_id: int) -> dict[str, Any]:
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_by_user_id, title, status, filters_json, created_at
                    FROM selection_requests
                    WHERE id = %s
                    """,
                    (request_id,),
                )
                request_row = cur.fetchone()
                if request_row is None:
                    raise NotFoundError("Request not found.")

                request = request_from_row(request_row)
                request["items"] = self._items_for_request(cur, request_id)
                request["approval"] = self._approval_for_request(cur, request_id)
                request["export"] = self._export_for_request(cur, request_id)
                return request

    def _list_requests(self, query: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                requests = [request_from_row(row) for row in cur.fetchall()]
                for request in requests:
                    request["items"] = self._items_for_request(cur, request["id"])
                    request["approval"] = self._approval_for_request(cur, request["id"])
                    request["export"] = self._export_for_request(cur, request["id"])
                return requests

    def _items_for_request(self, cur: Any, request_id: int) -> list[dict[str, Any]]:
        cur.execute(
            """
            SELECT id, request_id, orthanc_study_id
            FROM selection_items
            WHERE request_id = %s
            ORDER BY id ASC
            """,
            (request_id,),
        )
        return [
            {
                "id": row[0],
                "request_id": row[1],
                "orthanc_study_id": row[2],
                "study_info": self._study_info(row[2]),
            }
            for row in cur.fetchall()
        ]

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

    def _approval_for_request(self, cur: Any, request_id: int) -> dict[str, Any] | None:
        cur.execute(
            """
            SELECT id, request_id, decided_by_user_id, decision, reason, decided_at
            FROM approvals
            WHERE request_id = %s
            ORDER BY decided_at DESC, id DESC
            LIMIT 1
            """,
            (request_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "request_id": row[1],
            "decided_by_user_id": row[2],
            "decision": row[3],
            "reason": row[4],
            "decided_at": row[5].isoformat(),
        }

    def _export_for_request(self, cur: Any, request_id: int) -> dict[str, Any] | None:
        cur.execute(
            """
            SELECT id, request_id, status, export_path, manifest_path, error, created_at, updated_at,
                   request_hash, reused_from_export_id
            FROM request_exports
            WHERE request_id = %s
            """,
            (request_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return export_from_row(row)

    def _ensure_owner(self, request: dict[str, Any], user: dict[str, Any]) -> None:
        if request["created_by_user_id"] != user["id"]:
            raise ForbiddenMutationError("Researchers can only mutate their own requests.")

    def _ensure_status(self, request: dict[str, Any], expected_status: str) -> None:
        if request["status"] != expected_status:
            raise InvalidStateError(f"Request must be {expected_status}, current status is {request['status']}.")


def request_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "created_by_user_id": row[1],
        "title": row[2],
        "status": row[3],
        "filters_json": row[4],
        "created_at": row[5].isoformat(),
    }


def normalize_decision(decision: str) -> str:
    normalized = decision.strip().upper()
    if normalized == "APPROVE":
        return "APPROVED"
    if normalized == "REJECT":
        return "REJECTED"
    if normalized in {"APPROVED", "REJECTED"}:
        return normalized
    raise ValueError("'decision' must be APPROVE, REJECT, APPROVED, or REJECTED.")
