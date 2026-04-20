import hashlib
import json
import os
import re
from shutil import copy2
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.database import Database
from app.services.orthanc_client import OrthancClient


SAFE_PATH_RE = re.compile(r"[^A-Za-z0-9_.-]+")


class ExportService:
    def __init__(self, database: Database, export_root: str, orthanc: OrthancClient | None = None) -> None:
        self.database = database
        self.export_root = Path(export_root)
        self.orthanc = orthanc

    def prepare_approved_export(self, request: dict[str, Any], decided_by: dict[str, Any]) -> dict[str, Any]:
        request_id = int(request["id"])
        export_dir = self.export_root / "requests" / str(request_id)
        manifest_path = export_dir / "manifest.json"
        request_hash = compute_request_hash([item["orthanc_study_id"] for item in request.get("items", [])])
        reusable_export = self._find_reusable_export(request_hash, request_id)
        export = self._upsert_export(
            request_id=request_id,
            status="PENDING",
            export_path=str(export_dir),
            manifest_path=str(manifest_path),
            error=None,
            request_hash=request_hash,
            reused_from_export_id=reusable_export["id"] if reusable_export else None,
        )

        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            if reusable_export:
                exported_instances = self._reuse_export_items(reusable_export["id"], export_dir)
            else:
                exported_instances = self._export_instances(request, export_dir)
            manifest = self._manifest(request, decided_by, export_dir, exported_instances, request_hash, reusable_export)
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            self._replace_export_items(export["id"], exported_instances)
        except Exception as exc:
            return self._upsert_export(
                request_id=request_id,
                status="FAILED",
                export_path=str(export_dir),
                manifest_path=str(manifest_path),
                error=str(exc),
                request_hash=request_hash,
                reused_from_export_id=reusable_export["id"] if reusable_export else None,
            )

        return self._upsert_export(
            request_id=request_id,
            status="READY",
            export_path=str(export_dir),
            manifest_path=str(manifest_path),
            error=None,
            request_hash=request_hash,
            reused_from_export_id=reusable_export["id"] if reusable_export else None,
        )

    def _export_instances(self, request: dict[str, Any], export_dir: Path) -> list[dict[str, Any]]:
        if self.orthanc is None:
            raise RuntimeError("Orthanc client is required for approved export file preparation.")

        instance_store = self.export_root / "instances"
        instance_store.mkdir(parents=True, exist_ok=True)
        exported_instances: list[dict[str, Any]] = []
        seen_instances: set[str] = set()

        for item in request.get("items", []):
            study_id = item["orthanc_study_id"]
            study = self.orthanc.get_study(study_id)
            for series_id in study.get("Series", []):
                for instance_id in self._series_instance_ids(str(series_id)):
                    if instance_id in seen_instances:
                        continue
                    seen_instances.add(instance_id)

                    filename = f"{safe_path_component(instance_id)}.dcm"
                    stored_file = instance_store / filename
                    linked_file = export_dir / filename

                    if not stored_file.exists():
                        stored_file.write_bytes(self.orthanc.get_instance_file(instance_id))

                    hardlinked = make_hardlink(stored_file, linked_file)
                    exported_instances.append(
                        {
                            "orthanc_study_id": study_id,
                            "orthanc_series_id": str(series_id),
                            "orthanc_instance_id": instance_id,
                            "stored_file": str(stored_file),
                            "linked_file": str(linked_file),
                            "hardlinked": hardlinked,
                        }
                    )

        return exported_instances

    def _series_instance_ids(self, series_id: str) -> list[str]:
        instance_ids: list[str] = []
        for item in self.orthanc.get_series_instances(series_id):
            if isinstance(item, dict) and isinstance(item.get("ID"), str):
                instance_ids.append(item["ID"])
            elif isinstance(item, str):
                instance_ids.append(item)
        return instance_ids

    def _reuse_export_items(self, reused_from_export_id: int, export_dir: Path) -> list[dict[str, Any]]:
        exported_instances: list[dict[str, Any]] = []
        for item in self._export_items(reused_from_export_id):
            stored_file = Path(item["stored_file"])
            linked_file = export_dir / stored_file.name
            hardlinked = make_hardlink(stored_file, linked_file)
            exported_instances.append(
                {
                    "orthanc_study_id": item["orthanc_study_id"],
                    "orthanc_series_id": item["orthanc_series_id"],
                    "orthanc_instance_id": item["orthanc_instance_id"],
                    "stored_file": str(stored_file),
                    "linked_file": str(linked_file),
                    "hardlinked": hardlinked,
                    "reused": True,
                }
            )
        return exported_instances

    def _manifest(
        self,
        request: dict[str, Any],
        decided_by: dict[str, Any],
        export_dir: Path,
        exported_instances: list[dict[str, Any]],
        request_hash: str,
        reusable_export: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "request_id": request["id"],
            "request_hash": request_hash,
            "title": request["title"],
            "status": request["status"],
            "created_by_user_id": request["created_by_user_id"],
            "approved_by_user_id": decided_by["id"],
            "approved_by_username": decided_by["username"],
            "reused_from_export_id": reusable_export["id"] if reusable_export else None,
            "reused_from_request_id": reusable_export["request_id"] if reusable_export else None,
            "filters_json": request.get("filters_json") or {},
            "selected_studies": [
                {
                    "orthanc_study_id": item["orthanc_study_id"],
                    "study_info": item.get("study_info"),
                }
                for item in request.get("items", [])
            ],
            "export_path": str(export_dir),
            "instance_count": len(exported_instances),
            "instances": exported_instances,
            "created_at": datetime.now(UTC).isoformat(),
            "note": "Story 9 export. Same selections reuse earlier READY exports; otherwise DICOM files are downloaded and hardlinked.",
        }

    def _find_reusable_export(self, request_hash: str, request_id: int) -> dict[str, Any] | None:
        with self.database.connect() as conn:
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

    def _export_items(self, export_id: int) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
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

    def _replace_export_items(self, export_id: int, exported_instances: list[dict[str, Any]]) -> None:
        with self.database.connect() as conn:
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
                conn.commit()

    def _upsert_export(
        self,
        request_id: int,
        status: str,
        export_path: str,
        manifest_path: str,
        error: str | None,
        request_hash: str,
        reused_from_export_id: int | None,
    ) -> dict[str, Any]:
        with self.database.connect() as conn:
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
                row = cur.fetchone()
                conn.commit()
        return export_from_row(row)


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


def compute_request_hash(orthanc_study_ids: list[str]) -> str:
    normalized = "\n".join(sorted(set(orthanc_study_ids)))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def safe_path_component(value: str) -> str:
    value = value.strip()
    if not value:
        return "item"
    return SAFE_PATH_RE.sub("_", value)


def make_hardlink(source: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return True
    try:
        os.link(source, target)
        return True
    except OSError:
        copy2(source, target)
        return False
