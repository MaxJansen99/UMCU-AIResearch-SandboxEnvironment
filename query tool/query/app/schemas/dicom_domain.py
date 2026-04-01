from pydantic import BaseModel, Field


class InstanceSummary(BaseModel):
    sop_instance_uid: str
    instance_number: int | None = None
    file_path: str
    modality: str | None = None


class SeriesSummary(BaseModel):
    series_instance_uid: str
    study_instance_uid: str
    series_description: str | None = None
    modality: str | None = None
    body_part_examined: str | None = None
    instance_count: int = 0


class StudySummary(BaseModel):
    study_instance_uid: str
    patient_id: str | None = None
    patient_name: str | None = None
    study_date: str | None = None
    study_description: str | None = None
    accession_number: str | None = None
    modalities: list[str] = Field(default_factory=list)
    series_count: int = 0
    instance_count: int = 0


class StudyDetail(StudySummary):
    series: list[SeriesSummary] = Field(default_factory=list)


class SeriesDetail(SeriesSummary):
    instances: list[InstanceSummary] = Field(default_factory=list)

