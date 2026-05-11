from collections import Counter
from time import perf_counter
from typing import Any

from app.domain.operators import HIDDEN_TAGS, ALLOWED_TAGS, OPERATORS, FilterSpec, normalize_filter_specs
from app.services.orthanc_client import OrthancClient
from app.services.orthanc_tags import normalize_orthanc_dicom_tags, safe_get_full


def _stats_key(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _summarize_stats(stats_counters: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {tag: dict(counter.most_common()) for tag, counter in stats_counters.items()}


class QueryService:
    def __init__(self, orthanc: OrthancClient) -> None:
        self.orthanc = orthanc

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw_filters = payload.get("filters", [])
        if not isinstance(raw_filters, list):
            raise ValueError("'filters' must be a list.")

        stats_tags = payload.get("stats_tags", [])
        if not isinstance(stats_tags, list) or not all(isinstance(tag, str) for tag in stats_tags):
            raise ValueError("'stats_tags' must be a list of strings.")

        filters = normalize_filter_specs(raw_filters)
        started_at = perf_counter()
        response = self.query(filters, stats_tags)
        response["elapsed_seconds"] = perf_counter() - started_at
        return response

    def query(self, filters: list[FilterSpec], stats_tags: list[str]) -> dict[str, Any]:
        total_instances = self._instance_count()
        usable_filters = [spec for spec in filters if spec[0] in ALLOWED_TAGS]
        stats_tags = ALLOWED_TAGS

        query_body: dict[str, Any] = {}
        for tag_name, operator_name, expected in usable_filters:
            if operator_name == "==":
                query_body[tag_name] = expected

        # geef series ID's die bij metadata selectie passen
        series_ids = self.orthanc.find_series(query_body)
        stats_counters: dict[str, Counter] = {tag: Counter() for tag in stats_tags}
        matched: list[dict[str, Any]] = []
        study_cache: dict[str, dict[str, Any]] = {}

        for series_id in series_ids:
            meta = self.orthanc.get_series(series_id)
            meta = self._with_study_tags(meta, study_cache)
            if not self._matches(meta, usable_filters):
                continue

            matched.append({"id": series_id, "meta": meta})

            for tag in stats_tags:
                value = safe_get_full(meta, tag)
                if value is not None:
                    stats_counters[tag][_stats_key(value)] += 1

        return {
            "ok": True,
            "root": self.orthanc.base_url,
            "pacs": True,
            "filters": usable_filters,
            "total_instances_in_pacs": total_instances,
            "total_series_found": len(series_ids),
            "match_count": len(matched),
            "matches": [item["id"] for item in matched],
            "matched_series": [self._series_summary(item["id"], item["meta"]) for item in matched],
            "stats": _summarize_stats(stats_counters),
        }

    def collect_all_stats(self) -> tuple[dict[str, dict[str, int]], int, int]:
        stats_counters: dict[str, Counter] = {}
        total_series = 0
        total_instances = 0

        for series_id in self.orthanc.find_series():
            total_series += 1
            try:
                series_meta = self.orthanc.get_series(series_id)
            except Exception:
                continue

            for tag, value in series_meta.get("MainDicomTags", {}).items():
                stats_counters.setdefault(tag, Counter())[_stats_key(value)] += 1

            for instance in self.orthanc.get_series_instances(series_id):
                instance_id = instance.get("ID") if isinstance(instance, dict) else None
                if not instance_id:
                    continue
                total_instances += 1
                try:
                    instance_tags = normalize_orthanc_dicom_tags(self.orthanc.get_instance_tags(instance_id))
                except Exception:
                    continue
                for tag, value in instance_tags.items():
                    if tag in HIDDEN_TAGS:
                        continue
                    stats_counters.setdefault(tag, Counter())[_stats_key(value)] += 1

        return _summarize_stats(stats_counters), total_series, total_instances

    def _instance_count(self) -> int:
        try:
            return int(self.orthanc.health().get("CountInstances", 0))
        except Exception:
            return 0

    def _matches(self, meta: dict[str, Any], filters: list[FilterSpec]) -> bool:
        for tag_name, operator_name, expected in filters:
            actual = safe_get_full(meta, tag_name)
            if not OPERATORS[operator_name](actual, expected):
                return False
        return True

    def _series_summary(self, series_id: str, meta: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": series_id,
            "orthanc_study_id": meta.get("ParentStudy", ""),
            "study_instance_uid": safe_get_full(meta, "StudyInstanceUID") or "",
            "series_instance_uid": safe_get_full(meta, "SeriesInstanceUID") or "",
            "modality": safe_get_full(meta, "Modality") or "",
            "patient_id": safe_get_full(meta, "PatientID") or "",
            "patient_birth_date": safe_get_full(meta, "PatientBirthDate") or "",
            "patient_sex": safe_get_full(meta, "PatientSex") or "",
            "study_date": safe_get_full(meta, "StudyDate") or "",
            "study_description": safe_get_full(meta, "StudyDescription") or "",
            "series_description": safe_get_full(meta, "SeriesDescription") or "",
            "body_part_examined": safe_get_full(meta, "BodyPartExamined") or "",
            "instances": len(meta.get("Instances", [])),
        }

    def _with_study_tags(self, meta: dict[str, Any], study_cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
        study_id = meta.get("ParentStudy")
        if not study_id:
            return meta

        if study_id not in study_cache:
            try:
                study_cache[study_id] = self.orthanc.get_study(str(study_id))
            except Exception:
                study_cache[study_id] = {}

        study = study_cache[study_id]
        return {
            **meta,
            "StudyMainDicomTags": study.get("MainDicomTags", {}),
            "PatientMainDicomTags": study.get("PatientMainDicomTags", {}),
        }
