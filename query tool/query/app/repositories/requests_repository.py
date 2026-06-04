from typing import Any

import psycopg
from psycopg.types.json import Jsonb


class RequestsRepository:
    def create_request(
        self,
        conn: psycopg.Connection,
        created_by_user_id: int,
        title: str,
        filters_json: dict[str, Any] | None,
    ) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO selection_requests (created_by_user_id, title, status, filters_json)
                VALUES (%s, %s, 'DRAFT', %s)
                RETURNING id
                """,
                (created_by_user_id, title, Jsonb(filters_json or {})),
            )
            return int(cur.fetchone()[0])

    def add_items(self, conn: psycopg.Connection, request_id: int, orthanc_study_ids: list[str]) -> None:
        with conn.cursor() as cur:
            for orthanc_study_id in orthanc_study_ids:
                cur.execute(
                    """
                    INSERT INTO selection_items (request_id, orthanc_study_id)
                    VALUES (%s, %s)
                    """,
                    (request_id, orthanc_study_id),
                )

    def update_status(self, conn: psycopg.Connection, request_id: int, status: str) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE selection_requests
                SET status = %s
                WHERE id = %s
                """,
                (status, request_id),
            )

    def add_approval(
        self,
        conn: psycopg.Connection,
        request_id: int,
        decided_by_user_id: int,
        decision: str,
        reason: str | None,
    ) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO approvals (request_id, decided_by_user_id, decision, reason)
                VALUES (%s, %s, %s, %s)
                """,
                (request_id, decided_by_user_id, decision, reason),
            )

    def get_request(self, conn: psycopg.Connection, request_id: int) -> dict[str, Any] | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_by_user_id, title, status, filters_json, created_at
                FROM selection_requests
                WHERE id = %s
                """,
                (request_id,),
            )
            row = cur.fetchone()
        return request_from_row(row)

    def list_by_creator(self, conn: psycopg.Connection, user_id: int) -> list[dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_by_user_id, title, status, filters_json, created_at
                FROM selection_requests
                WHERE created_by_user_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
        return [request_from_row(row) for row in rows]

    def list_pending(self, conn: psycopg.Connection) -> list[dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, created_by_user_id, title, status, filters_json, created_at
                FROM selection_requests
                WHERE status = 'SUBMITTED'
                ORDER BY created_at ASC, id ASC
                """
            )
            rows = cur.fetchall()
        return [request_from_row(row) for row in rows]

    def list_items(self, conn: psycopg.Connection, request_id: int) -> list[dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, request_id, orthanc_study_id
                FROM selection_items
                WHERE request_id = %s
                ORDER BY id ASC
                """,
                (request_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "request_id": row[1],
                "orthanc_study_id": row[2],
            }
            for row in rows
        ]

    def latest_approval(self, conn: psycopg.Connection, request_id: int) -> dict[str, Any] | None:
        with conn.cursor() as cur:
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


def request_from_row(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": row[0],
        "created_by_user_id": row[1],
        "title": row[2],
        "status": row[3],
        "filters_json": row[4],
        "created_at": row[5].isoformat(),
    }
