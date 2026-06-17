import csv
from pathlib import Path
from typing import Any


class CsvDataSourceError(ValueError):
    pass


TAG_ALIASES: dict[str, tuple[str, ...]] = {
    "Modality": ("Modality", "modality"),
    "PatientAge": ("PatientAge", "patient_age", "age"),
    "PatientBirthDate": ("PatientBirthDate", "patient_birth_date", "birth_date", "date_of_birth"),
    "PatientID": ("PatientID", "patient_id", "patient"),
    "PatientSex": ("PatientSex", "patient_sex", "sex", "gender"),
    "StudyDate": ("StudyDate", "study_date", "date"),
    "StudyDescription": ("StudyDescription", "study_description", "study"),
    "StudyInstanceUID": ("StudyInstanceUID", "study_instance_uid", "study_uid"),
    "SeriesDescription": ("SeriesDescription", "series_description", "series"),
    "SeriesInstanceUID": ("SeriesInstanceUID", "series_instance_uid", "series_uid"),
    "BodyPartExamined": ("BodyPartExamined", "body_part_examined", "body_part", "bodypart"),
    "Images": ("Images", "images", "instances", "instance_count"),
}

ID_ALIASES: dict[str, tuple[str, ...]] = {
    "series_id": ("id", "series_id", "orthanc_series_id", "SeriesID"),
    "study_id": ("orthanc_study_id", "study_id", "OrthancStudyID", "StudyID"),
}

DATE_TAGS = {"PatientBirthDate", "StudyDate"}
CORE_QUERY_TAGS = {"Modality", "PatientAge", "PatientBirthDate", "PatientSex", "StudyDate", "BodyPartExamined"}


class CsvDataSource:
    def __init__(self, csv_file: str) -> None:
        if not csv_file:
            raise ValueError("CSV fallback file is required.")
        self.csv_file = Path(csv_file)
        self.base_url = f"csv://{self.csv_file}"
        self._series: dict[str, dict[str, Any]] = {}
        self._studies: dict[str, dict[str, Any]] = {}
        self.warnings: list[str] = []
        self._load()

    def health(self) -> dict[str, Any]:
        return {
            "Source": "csv",
            "Path": str(self.csv_file),
            "CountSeries": len(self._series),
            "CountInstances": sum(_instance_count(series) for series in self._series.values()),
            "Warnings": self.warnings[:10],
            "WarningCount": len(self.warnings),
        }

    @property
    def source_name(self) -> str:
        return "csv"

    def source_info(self) -> dict[str, Any]:
        return {
            "ActiveSource": "csv",
            "Root": self.base_url,
            "CsvFile": str(self.csv_file),
            "WarningCount": len(self.warnings),
        }

    def find_series(self, query: dict[str, Any] | None = None) -> list[str]:
        query = query or {}
        if not query:
            return list(self._series)

        return [
            series_id
            for series_id, meta in self._series.items()
            if all(_safe_get(meta, tag) == expected for tag, expected in query.items())
        ]

    def get_series(self, series_id: str) -> dict[str, Any]:
        try:
            return self._series[series_id]
        except KeyError as exc:
            raise KeyError(f"CSV series not found: {series_id}") from exc

    def get_study(self, study_id: str) -> dict[str, Any]:
        return self._studies.get(study_id, {"ID": study_id, "MainDicomTags": {}, "PatientMainDicomTags": {}})

    def get_series_instances(self, series_id: str) -> list[Any]:
        series = self.get_series(series_id)
        return [{"ID": f"{series_id}-instance-{index + 1}"} for index in range(_instance_count(series))]

    def get_instance_tags(self, instance_id: str) -> dict[str, Any]:
        return {}

    def get_instance_file(self, instance_id: str) -> bytes:
        raise RuntimeError("CSV datasource does not provide DICOM instance files.")

    def _load(self) -> None:
        if not self.csv_file.is_file():
            raise CsvDataSourceError(f"CSV fallback file not found: {self.csv_file}")

        with self.csv_file.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise CsvDataSourceError("CSV fallback file must contain a header row.")

            column_lookup = {_normalize_column(name): name for name in reader.fieldnames if name}
            self._validate_header(reader.fieldnames, column_lookup)
            for row_number, row in enumerate(reader, start=2):
                normalized_row = {key: _normalize_cell(value) for key, value in row.items() if isinstance(key, str)}
                if not any(normalized_row.values()):
                    continue

                series_id = _value_from_aliases(normalized_row, column_lookup, ID_ALIASES["series_id"])
                study_id = _value_from_aliases(normalized_row, column_lookup, ID_ALIASES["study_id"])

                tags = {
                    tag: _normalize_tag_value(tag, _value_from_aliases(normalized_row, column_lookup, aliases))
                    for tag, aliases in TAG_ALIASES.items()
                }

                if not series_id:
                    series_id = tags["SeriesInstanceUID"] or f"csv-series-{row_number}"
                if not study_id:
                    study_id = tags["StudyInstanceUID"] or f"csv-study-{row_number}"
                series_id = self._unique_series_id(series_id, row_number)

                missing_core_tags = sorted(tag for tag in CORE_QUERY_TAGS if not tags.get(tag))
                if missing_core_tags:
                    self.warnings.append(
                        f"Row {row_number}: missing values for {', '.join(missing_core_tags)}."
                    )

                instance_count = _parse_positive_int(tags.pop("Images"), default=1)
                series_meta = {
                    "ID": series_id,
                    "ParentStudy": study_id,
                    "MainDicomTags": {
                        "Modality": tags["Modality"],
                        "SeriesInstanceUID": tags["SeriesInstanceUID"],
                        "SeriesDescription": tags["SeriesDescription"],
                        "BodyPartExamined": tags["BodyPartExamined"],
                    },
                    "StudyMainDicomTags": {
                        "StudyDate": tags["StudyDate"],
                        "StudyDescription": tags["StudyDescription"],
                        "StudyInstanceUID": tags["StudyInstanceUID"],
                    },
                    "PatientMainDicomTags": {
                        "PatientID": tags["PatientID"],
                        "PatientAge": tags["PatientAge"],
                        "PatientBirthDate": tags["PatientBirthDate"],
                        "PatientSex": tags["PatientSex"],
                    },
                    "InstancesCount": instance_count,
                    "Source": "csv",
                    "RawCsv": normalized_row,
                }
                self._series[series_id] = series_meta
                self._studies.setdefault(
                    study_id,
                    {
                        "ID": study_id,
                        "MainDicomTags": series_meta["StudyMainDicomTags"],
                        "PatientMainDicomTags": series_meta["PatientMainDicomTags"],
                        "Series": [],
                    },
                )
                self._studies[study_id]["Series"].append(series_id)

            if not self._series:
                raise CsvDataSourceError("CSV fallback file contains no usable data rows.")

    def _validate_header(self, fieldnames: list[str], column_lookup: dict[str, str]) -> None:
        duplicate_headers = _duplicate_normalized_headers(fieldnames)
        if duplicate_headers:
            raise CsvDataSourceError(
                "CSV fallback file contains duplicate/ambiguous columns after normalization: "
                + ", ".join(duplicate_headers)
            )

        recognized_tags = [
            tag
            for tag, aliases in TAG_ALIASES.items()
            if any(_normalize_column(alias) in column_lookup for alias in aliases)
        ]
        recognized_ids = [
            name
            for name, aliases in ID_ALIASES.items()
            if any(_normalize_column(alias) in column_lookup for alias in aliases)
        ]
        if not recognized_tags and not recognized_ids:
            raise CsvDataSourceError(
                "CSV fallback file does not contain recognized metadata columns. "
                "Use DICOM tags or aliases such as Modality/modality, StudyDate/study_date, "
                "BodyPartExamined/body_part."
            )

        if not any(tag in recognized_tags for tag in CORE_QUERY_TAGS):
            raise CsvDataSourceError(
                "CSV fallback file must contain at least one query metadata column, such as "
                "Modality, StudyDate, BodyPartExamined, PatientAge, PatientBirthDate or PatientSex."
            )

    def _unique_series_id(self, series_id: str, row_number: int) -> str:
        if series_id not in self._series:
            return series_id
        unique_id = f"{series_id}-row-{row_number}"
        self.warnings.append(f"Row {row_number}: duplicate series id '{series_id}', using '{unique_id}'.")
        return unique_id


def _normalize_column(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())


def _normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None).strip()
    return str(value).strip()


def _normalize_tag_value(tag: str, value: str) -> str:
    if tag in DATE_TAGS:
        digits = "".join(char for char in value if char.isdigit())
        if len(digits) == 8:
            return digits
    return value


def _duplicate_normalized_headers(fieldnames: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for fieldname in fieldnames:
        normalized = _normalize_column(fieldname)
        if not normalized:
            continue
        if normalized in seen:
            duplicates.add(normalized)
        seen.add(normalized)
    return sorted(duplicates)


def _value_from_aliases(row: dict[str, str], column_lookup: dict[str, str], aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        column = column_lookup.get(_normalize_column(alias))
        if column:
            return row.get(column, "")
    return ""


def _parse_positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _instance_count(series: dict[str, Any]) -> int:
    instances = series.get("Instances")
    if isinstance(instances, list):
        return len(instances)
    count = series.get("InstancesCount")
    return count if isinstance(count, int) and count > 0 else 0


def _safe_get(meta: dict[str, Any], key: str) -> Any:
    for section in ("MainDicomTags", "StudyMainDicomTags", "PatientMainDicomTags"):
        values = meta.get(section, {})
        if key in values:
            return values[key]
    return meta.get(key)
