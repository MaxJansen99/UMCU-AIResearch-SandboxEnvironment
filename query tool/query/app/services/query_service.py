from collections import Counter
from time import perf_counter
from typing import Any

from app.domain.operators import HIDDEN_TAGS, OPERATORS, FilterSpec, normalize_filter_specs
from app.services.orthanc_client import OrthancClient
from app.services.orthanc_tags import normalize_orthanc_dicom_tags, safe_get, safe_get_full


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
        usable_filters = [spec for spec in filters if spec[0] not in HIDDEN_TAGS]
        usable_stats_tags = [tag for tag in stats_tags if tag not in HIDDEN_TAGS]

        query_body: dict[str, Any] = {}
        for tag_name, operator_name, expected in usable_filters:
            if operator_name == "==":
                query_body[tag_name] = expected

        series_ids = self.orthanc.find_series(query_body)
        stats_counters: dict[str, Counter] = {tag: Counter() for tag in usable_stats_tags}
        matched: list[dict[str, Any]] = []

        for series_id in series_ids:
            meta = self.orthanc.get_series(series_id)
            meta = self._with_first_instance_tags(meta)
            if not self._matches(meta, usable_filters):
                continue

            matched.append({"id": series_id, "meta": meta})

            for tag in usable_stats_tags:
                value = safe_get(meta, tag)
                if value is not None:
                    stats_counters[tag][_stats_key(value)] += 1

            self._collect_instance_stats(series_id, meta, usable_filters, usable_stats_tags, stats_counters)

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

    def _collect_instance_stats(
        self,
        series_id: str,
        series_meta: dict[str, Any],
        filters: list[FilterSpec],
        stats_tags: list[str],
        stats_counters: dict[str, Counter],
    ) -> None:
        if not stats_tags:
            return

        try:
            instances = self.orthanc.get_series_instances(series_id)
        except Exception:
            return

        for instance in instances:
            instance_id = instance.get("ID") if isinstance(instance, dict) else None
            if not instance_id:
                continue
            try:
                instance_tags = normalize_orthanc_dicom_tags(self.orthanc.get_instance_tags(instance_id))
            except Exception:
                continue

            instance_meta = {
                "MainDicomTags": series_meta.get("MainDicomTags", {}),
                "DicomTags": instance_tags,
            }
            if not self._matches(instance_meta, filters):
                continue

            for tag in stats_tags:
                value = safe_get_full(instance_meta, tag)
                if value is not None:
                    stats_counters[tag][_stats_key(value)] += 1

    def _series_summary(self, series_id: str, meta: dict[str, Any]) -> dict[str, Any]:
        tags = meta.get("MainDicomTags", {})
        instance_tags = meta.get("DicomTags", {})
        return {
            "id": series_id,
            "study_instance_uid": tags.get("StudyInstanceUID", instance_tags.get("StudyInstanceUID", "")),
            "series_instance_uid": tags.get("SeriesInstanceUID", instance_tags.get("SeriesInstanceUID", "")),
            "modality": tags.get("Modality", instance_tags.get("Modality", "")),
            "study_date": tags.get("StudyDate", instance_tags.get("StudyDate", "")),
            "study_description": tags.get("StudyDescription", instance_tags.get("StudyDescription", "")),
            "series_description": tags.get("SeriesDescription", instance_tags.get("SeriesDescription", "")),
            "body_part_examined": tags.get("BodyPartExamined", instance_tags.get("BodyPartExamined", "")),
            "instances": len(meta.get("Instances", [])),
        }

    def _with_first_instance_tags(self, meta: dict[str, Any]) -> dict[str, Any]:
        if meta.get("DicomTags"):
            return meta

        instance_ids = meta.get("Instances", [])
        if instance_ids:
            try:
                return {
                    **meta,
                    "DicomTags": normalize_orthanc_dicom_tags(self.orthanc.get_instance_tags(instance_ids[0])),
                }
            except Exception:
                return meta

        return meta
