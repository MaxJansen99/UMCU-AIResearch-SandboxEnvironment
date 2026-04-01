from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    filters: list[list[Any]] = Field(default_factory=list)
    root: str | None = None
    recursive: bool = True
    stats_tags: list[str] = Field(default_factory=list)
    extra_tags: list[str] = Field(default_factory=list)


class QueryStudyMatch(BaseModel):
    study_instance_uid: str
    study_description: str | None = None
    study_date: str | None = None
    modalities: list[str] = Field(default_factory=list)
    series_count: int = 0
    instance_count: int = 0
    sample_paths: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    ok: bool
    root: str
    recursive: bool
    filters: list[list[Any]]
    study_count: int
    series_count: int
    image_count: int
    total_files: int
    dicom_files: int
    match_count: int
    matches: list[str]
    matched_studies: list[QueryStudyMatch]
    stats: dict[str, dict[str, int]]
    elapsed_seconds: float
