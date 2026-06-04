from typing import Any

import psycopg


class ExportsRepository:
    def upsert_export(
        self,
        conn: psycopg.Connection,
        request_id: int,
        status: str,
        export_path: str,
        manifest_path: str,
        error: str | None,
        request_hash: str,
        reused_from_export_id: int | None,
    ) -> dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO request_exports (
                    request_id,
                    request_hash,
                    reused_from_export_id,
                    status,
                    export_path,
                    manifest_path,
                    error
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (request_id) DO UPDATE
                SET request_hash = EXCLUDED.request_hash,
                    reused_from_export_id = EXCLUDED.reused_from_export_id,
                    status = EXCLUDED.status,
                    export_path = EXCLUDED.export_path,
                    manifest_path = EXCLUDED.manifest_path,
                    error = EXCLUDED.error,
                    updated_at = now()
                RETURNING id, request_id, status, export_path, manifest_path, error, created_at, updated_at,
                          request_hash, reused_from_export_id
                """,
                (
                    request_id,
                    request_hash,
                    reused_from_export_id,
                    status,
                    export_path,
                    manifest_path,
                    error,
                ),
            )
            return export_from_row(cur.fetchone())

    def find_by_request_id(self, conn: psycopg.Connection, request_id: int) -> dict[str, Any] | None:
        with conn.cursor() as cur:
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
        return export_from_row(row) if row else None

    def find_reusable_export(
        self,
        conn: psycopg.Connection,
        request_hash: str,
        request_id: int,
    ) -> dict[str, Any] | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, request_id, status, export_path, manifest_path, error, created_at, updated_at,
                       request_hash, reused_from_export_id
                FROM request_exports
                WHERE request_hash = %s
                  AND request_id <> %s
                  AND status = 'READY'
                ORDER BY updated_at DESC, id DESC
                LIMIT 1
                """,
                (request_hash, request_id),
            )
            row = cur.fetchone()
        return export_from_row(row) if row else None

    def list_export_items(self, conn: psycopg.Connection, export_id: int) -> list[dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT orthanc_study_id, orthanc_series_id, orthanc_instance_id, stored_file, linked_file
                FROM request_export_items
                WHERE export_id = %s
                ORDER BY id
                """,
                (export_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "orthanc_study_id": row[0],
                "orthanc_series_id": row[1],
                "orthanc_instance_id": row[2],
                "stored_file": row[3],
                "linked_file": row[4],
            }
            for row in rows
        ]

    def replace_export_items(
        self,
        conn: psycopg.Connection,
        export_id: int,
        exported_instances: list[dict[str, Any]],
    ) -> None:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM request_export_items WHERE export_id = %s", (export_id,))
            for item in exported_instances:
                cur.execute(
                    """
                    INSERT INTO request_export_items (
                        export_id,
                        orthanc_study_id,
                        orthanc_series_id,
                        orthanc_instance_id,
                        stored_file,
                        linked_file
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (export_id, orthanc_instance_id) DO NOTHING
                    """,
                    (
                        export_id,
                        item["orthanc_study_id"],
                        item["orthanc_series_id"],
                        item["orthanc_instance_id"],
                        item["stored_file"],
                        item["linked_file"],
                    ),
                )


def export_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": row[0],
        "request_id": row[1],
        "status": row[2],
        "export_path": row[3],
        "manifest_path": row[4],
        "error": row[5],
        "created_at": row[6].isoformat(),
        "updated_at": row[7].isoformat(),
        "request_hash": row[8] if len(row) > 8 else None,
        "reused_from_export_id": row[9] if len(row) > 9 else None,
    }
