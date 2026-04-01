import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pydicom import dcmread
from pydicom.dataset import Dataset

from app.schemas.dicom_domain import (
    InstanceSummary,
    SeriesDetail,
    SeriesSummary,
    StudyDetail,
    StudySummary,
)


DOMAIN_TAGS = [
    "PatientID",
    "PatientName",
    "StudyInstanceUID",
    "StudyDate",
    "StudyDescription",
    "AccessionNumber",
    "SeriesInstanceUID",
    "SeriesDescription",
    "Modality",
    "BodyPartExamined",
    "SOPInstanceUID",
    "InstanceNumber",
]


@dataclass
class DicomRecord:
    file_path: str
    patient_id: str | None
    patient_name: str | None
    study_instance_uid: str | None
    study_date: str | None
    study_description: str | None
    accession_number: str | None
    series_instance_uid: str | None
    series_description: str | None
    modality: str | None
    body_part_examined: str | None
    sop_instance_uid: str | None
    instance_number: int | None


class DicomDomainService:
    def list_studies(self, root: str) -> list[StudySummary]:
        studies, _, _ = self._build_index(root)
        return sorted(studies.values(), key=lambda study: (study.study_date or "", study.study_instance_uid))

    def get_study(self, root: str, study_instance_uid: str) -> StudyDetail:
        studies, series_by_study, _ = self._build_index(root)
        study = studies.get(study_instance_uid)
        if study is None:
            raise ValueError(f"Study not found: {study_instance_uid}")

        return StudyDetail(
            **study.model_dump(),
            series=sorted(
                [self._series_summary_from_detail(item) for item in series_by_study.get(study_instance_uid, [])],
                key=lambda series: (series.modality or "", series.series_instance_uid),
            ),
        )

    def list_series(self, root: str, study_instance_uid: str | None = None) -> list[SeriesSummary]:
        _, series_by_study, series_details = self._build_index(root)
        if study_instance_uid:
            return sorted(
                [self._series_summary_from_detail(item) for item in series_by_study.get(study_instance_uid, [])],
                key=lambda series: (series.modality or "", series.series_instance_uid),
            )

        all_series = [self._series_summary_from_detail(detail) for detail in series_details.values()]
        return sorted(all_series, key=lambda series: (series.study_instance_uid, series.modality or "", series.series_instance_uid))

    def get_series(self, root: str, series_instance_uid: str) -> SeriesDetail:
        _, _, series_details = self._build_index(root)
        series = series_details.get(series_instance_uid)
        if series is None:
            raise ValueError(f"Series not found: {series_instance_uid}")
        return series

    def list_instances(self, root: str, series_instance_uid: str) -> list[InstanceSummary]:
        series = self.get_series(root, series_instance_uid)
        return sorted(
            series.instances,
            key=lambda instance: (instance.instance_number if instance.instance_number is not None else 10**9, instance.sop_instance_uid),
        )

    def _build_index(
        self,
        root: str,
    ) -> tuple[
        dict[str, StudySummary],
        dict[str, list[SeriesDetail]],
        dict[str, SeriesDetail],
    ]:
        if not os.path.isdir(root):
            raise ValueError(f"DICOM root does not exist: {root}")

        studies: dict[str, StudySummary] = {}
        series_by_study: dict[str, list[SeriesDetail]] = defaultdict(list)
        series_details: dict[str, SeriesDetail] = {}

        for record in self._iter_records(root):
            if not record.study_instance_uid or not record.series_instance_uid or not record.sop_instance_uid:
                continue

            study = studies.get(record.study_instance_uid)
            if study is None:
                study = StudySummary(
                    study_instance_uid=record.study_instance_uid,
                    patient_id=record.patient_id,
                    patient_name=record.patient_name,
                    study_date=record.study_date,
                    study_description=record.study_description,
                    accession_number=record.accession_number,
                )
                studies[record.study_instance_uid] = study

            series = series_details.get(record.series_instance_uid)
            if series is None:
                series = SeriesDetail(
                    series_instance_uid=record.series_instance_uid,
                    study_instance_uid=record.study_instance_uid,
                    series_description=record.series_description,
                    modality=record.modality,
                    body_part_examined=record.body_part_examined,
                )
                series_details[record.series_instance_uid] = series
                series_by_study[record.study_instance_uid].append(series)
                study.series_count += 1

            series.instances.append(
                InstanceSummary(
                    sop_instance_uid=record.sop_instance_uid,
                    instance_number=record.instance_number,
                    file_path=record.file_path,
                    modality=record.modality,
                )
            )
            series.instance_count += 1
            study.instance_count += 1
            if record.modality and record.modality not in study.modalities:
                study.modalities.append(record.modality)

        for study in studies.values():
            study.modalities.sort()

        return studies, series_by_study, series_details

    def _iter_records(self, root: str) -> list[DicomRecord]:
        records: list[DicomRecord] = []
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                dataset = self._read_dataset(file_path)
                if dataset is None:
                    continue
                records.append(self._dataset_to_record(file_path, dataset))
        return records

    def _read_dataset(self, file_path: str) -> Dataset | None:
        try:
            return dcmread(
                file_path,
                stop_before_pixels=True,
                specific_tags=DOMAIN_TAGS,
            )
        except Exception:
            return None

    def _dataset_to_record(self, file_path: str, dataset: Dataset) -> DicomRecord:
        return DicomRecord(
            file_path=file_path,
            patient_id=self._to_text(getattr(dataset, "PatientID", None)),
            patient_name=self._to_text(getattr(dataset, "PatientName", None)),
            study_instance_uid=self._to_text(getattr(dataset, "StudyInstanceUID", None)),
            study_date=self._to_text(getattr(dataset, "StudyDate", None)),
            study_description=self._to_text(getattr(dataset, "StudyDescription", None)),
            accession_number=self._to_text(getattr(dataset, "AccessionNumber", None)),
            series_instance_uid=self._to_text(getattr(dataset, "SeriesInstanceUID", None)),
            series_description=self._to_text(getattr(dataset, "SeriesDescription", None)),
            modality=self._to_text(getattr(dataset, "Modality", None)),
            body_part_examined=self._to_text(getattr(dataset, "BodyPartExamined", None)),
            sop_instance_uid=self._to_text(getattr(dataset, "SOPInstanceUID", None)),
            instance_number=self._to_int(getattr(dataset, "InstanceNumber", None)),
        )

    def _series_summary_from_detail(self, series: SeriesDetail) -> SeriesSummary:
        return SeriesSummary(
            series_instance_uid=series.series_instance_uid,
            study_instance_uid=series.study_instance_uid,
            series_description=series.series_description,
            modality=series.modality,
            body_part_examined=series.body_part_examined,
            instance_count=series.instance_count,
        )

    def _to_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _to_int(self, value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
