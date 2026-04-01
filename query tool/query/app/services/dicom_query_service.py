import operator
import os
from collections import Counter
from time import perf_counter
from typing import Any, Callable

from pydicom import dcmread
from pydicom.dataset import Dataset

from app.schemas.query import QueryRequest, QueryResponse, QueryStudyMatch


FilterOperator = Callable[[Any, Any], bool]
FilterSpec = tuple[str, str, Any]


def op_contains(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and str(expected) in str(actual)


def op_startswith(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and str(actual).startswith(str(expected))


def op_endswith(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and str(actual).endswith(str(expected))


def op_in(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and actual in expected


def op_not_in(actual: Any, expected: Any) -> bool:
    return actual is not None and expected is not None and actual not in expected


def op_is_none(actual: Any, _: Any) -> bool:
    return actual is None


def op_not_none(actual: Any, _: Any) -> bool:
    return actual is not None


OPERATORS: dict[str, FilterOperator] = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": lambda actual, expected: actual is not None and expected is not None and actual > expected,
    ">=": lambda actual, expected: actual is not None and expected is not None and actual >= expected,
    "<": lambda actual, expected: actual is not None and expected is not None and actual < expected,
    "<=": lambda actual, expected: actual is not None and expected is not None and actual <= expected,
    "contains": op_contains,
    "startswith": op_startswith,
    "endswith": op_endswith,
    "in": op_in,
    "not in": op_not_in,
    "is None": op_is_none,
    "not None": op_not_none,
}

REGION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Brain", ("brain", "head", "neuro", "cranium")),
    ("Spine", ("spine", "cervical", "thoracic", "lumbar")),
    ("Chest", ("chest", "thorax", "lung")),
    ("Abdomen", ("abdomen", "abdominal", "liver")),
    ("Pelvis", ("pelvis", "pelvic", "hip")),
    ("Breast", ("breast", "mamma")),
    ("Knee", ("knee",)),
    ("Shoulder", ("shoulder",)),
    ("Whole body", ("whole body", "wholebody")),
]


class DicomQueryService:
    def run_query(self, payload: QueryRequest, default_root: str) -> QueryResponse:
        filter_specs = self._normalize_filters(payload.filters)
        root = payload.root or default_root

        if not root:
            raise ValueError("A DICOM root directory is required.")
        if not os.path.isdir(root):
            raise ValueError(f"DICOM root does not exist: {root}")

        started_at = perf_counter()
        matches, total_files, dicom_files, stats, summary, matched_studies = self._filter_files(
            root=root,
            filter_specs=filter_specs,
            recursive=payload.recursive,
            extra_tags=payload.extra_tags,
            stats_tags=payload.stats_tags,
        )
        elapsed_seconds = perf_counter() - started_at

        return QueryResponse(
            ok=True,
            root=root,
            recursive=payload.recursive,
            filters=[list(item) for item in filter_specs],
            study_count=summary["study_count"],
            series_count=summary["series_count"],
            image_count=summary["image_count"],
            total_files=total_files,
            dicom_files=dicom_files,
            match_count=len(matches),
            matches=matches,
            matched_studies=matched_studies,
            stats=stats,
            elapsed_seconds=elapsed_seconds,
        )

    def _normalize_filters(self, raw_filters: list[list[Any]]) -> list[FilterSpec]:
        normalized: list[FilterSpec] = []

        for raw_filter in raw_filters:
            if len(raw_filter) != 3:
                raise ValueError(
                    "Each filter must contain exactly 3 items: [tag_name, operator, value]."
                )

            name, operator_name, expected = raw_filter
            if not isinstance(name, str) or not name:
                raise ValueError("Filter tag_name must be a non-empty string.")
            if not isinstance(operator_name, str) or operator_name not in OPERATORS:
                raise ValueError(
                    f"Unsupported operator: {operator_name}. Supported operators: {sorted(OPERATORS)}"
                )

            normalized.append((name, operator_name, expected))

        return normalized

    def _filter_files(
        self,
        root: str,
        filter_specs: list[FilterSpec],
        recursive: bool,
        extra_tags: list[str],
        stats_tags: list[str],
    ) -> tuple[list[str], int, int, dict[str, dict[str, int]], dict[str, int], list[QueryStudyMatch]]:
        tags_to_read = list(dict.fromkeys([
            *self._required_tags(filter_specs),
            *extra_tags,
            *stats_tags,
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "SOPInstanceUID",
            "StudyDate",
            "StudyDescription",
            "Modality",
        ]))
        stats_counters: dict[str, Counter[str]] = {
            tag: Counter() for tag in stats_tags
        }
        matched_studies: set[str] = set()
        matched_series: set[str] = set()
        matched_images: set[str] = set()
        study_summaries: dict[str, dict[str, Any]] = {}

        matched: list[str] = []
        total_files = 0
        dicom_files = 0

        for path in self._iter_file_paths(root, recursive):
            total_files += 1
            dataset = self._read_dataset(path, tags_to_read)
            if dataset is None:
                continue

            dicom_files += 1
            if not self._matches_filters(dataset, filter_specs):
                continue

            matched.append(path)
            study_instance_uid = self._to_text(getattr(dataset, "StudyInstanceUID", None))
            series_instance_uid = self._to_text(getattr(dataset, "SeriesInstanceUID", None))
            sop_instance_uid = self._to_text(getattr(dataset, "SOPInstanceUID", None))
            if study_instance_uid:
                matched_studies.add(study_instance_uid)
                study_summary = study_summaries.setdefault(
                    study_instance_uid,
                    {
                        "study_instance_uid": study_instance_uid,
                        "study_description": self._to_text(getattr(dataset, "StudyDescription", None)),
                        "study_date": self._to_text(getattr(dataset, "StudyDate", None)),
                        "modalities": set(),
                        "series_uids": set(),
                        "instance_count": 0,
                        "sample_paths": [],
                    },
                )
                modality = self._to_text(getattr(dataset, "Modality", None))
                if modality:
                    study_summary["modalities"].add(modality)
                if series_instance_uid:
                    study_summary["series_uids"].add(series_instance_uid)
                study_summary["instance_count"] += 1
                if len(study_summary["sample_paths"]) < 3:
                    study_summary["sample_paths"].append(path)
            if series_instance_uid:
                matched_series.add(series_instance_uid)
            if sop_instance_uid:
                matched_images.add(sop_instance_uid)
            for tag in stats_tags:
                stats_counters[tag][self._stats_key(getattr(dataset, tag, None))] += 1

        stats = {tag: dict(counter.most_common()) for tag, counter in stats_counters.items()}
        summary = {
            "study_count": len(matched_studies),
            "series_count": len(matched_series),
            "image_count": len(matched_images) if matched_images else len(matched),
        }
        matched_study_items = [
            QueryStudyMatch(
                study_instance_uid=item["study_instance_uid"],
                study_description=item["study_description"],
                study_date=item["study_date"],
                modalities=sorted(item["modalities"]),
                series_count=len(item["series_uids"]),
                instance_count=item["instance_count"],
                sample_paths=item["sample_paths"],
            )
            for item in sorted(
                study_summaries.values(),
                key=lambda item: ((item["study_date"] or ""), (item["study_description"] or ""), item["study_instance_uid"]),
            )
        ]
        return matched, total_files, dicom_files, stats, summary, matched_study_items

    def _iter_file_paths(self, root: str, recursive: bool) -> list[str]:
        if recursive:
            file_paths: list[str] = []
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    file_paths.append(os.path.join(dirpath, filename))
            return file_paths

        return [
            os.path.join(root, filename)
            for filename in os.listdir(root)
            if os.path.isfile(os.path.join(root, filename))
        ]

    def _read_dataset(self, path: str, tags_to_read: list[str]) -> Dataset | None:
        try:
            return dcmread(
                path,
                stop_before_pixels=True,
                specific_tags=tags_to_read or None,
            )
        except Exception:
            return None

    def _matches_filters(self, dataset: Dataset, filter_specs: list[FilterSpec]) -> bool:
        for tag_name, operator_name, expected in filter_specs:
            actual = self._resolve_filter_value(dataset, tag_name)
            if not OPERATORS[operator_name](actual, expected):
                return False
        return True

    def _stats_key(self, value: Any) -> str:
        if value is None:
            return "<missing>"
        if isinstance(value, (list, tuple)):
            return ", ".join(str(item) for item in value)
        return str(value)

    def _to_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _required_tags(self, filter_specs: list[FilterSpec]) -> list[str]:
        tags: list[str] = []
        for tag_name, _, _ in filter_specs:
            if tag_name == "AnatomicalRegion":
                tags.extend(["BodyPartExamined", "StudyDescription", "SeriesDescription"])
            else:
                tags.append(tag_name)
        return tags

    def _resolve_filter_value(self, dataset: Dataset, tag_name: str) -> Any:
        if tag_name == "AnatomicalRegion":
            return self._infer_anatomical_region(dataset)
        return getattr(dataset, tag_name, None)

    def _infer_anatomical_region(self, dataset: Dataset) -> str | None:
        explicit = self._to_text(getattr(dataset, "BodyPartExamined", None))
        if explicit:
            return explicit

        searchable_text = " ".join(
            filter(
                None,
                [
                    self._to_text(getattr(dataset, "StudyDescription", None)),
                    self._to_text(getattr(dataset, "SeriesDescription", None)),
                ],
            )
        ).lower()

        for label, keywords in REGION_RULES:
            if any(keyword in searchable_text for keyword in keywords):
                return label

        return None
