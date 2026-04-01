from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.schemas.dicom_domain import (
    InstanceSummary,
    SeriesDetail,
    SeriesSummary,
    StudyDetail,
    StudySummary,
)
from app.services.dicom_domain_service import DicomDomainService


router = APIRouter(prefix="/dicom", tags=["dicom-domain"])
service = DicomDomainService()


@router.get("/studies", response_model=list[StudySummary])
def list_studies() -> list[StudySummary]:
    return service.list_studies(settings.dicom_root)


@router.get("/studies/{study_instance_uid}", response_model=StudyDetail)
def get_study(study_instance_uid: str) -> StudyDetail:
    try:
        return service.get_study(settings.dicom_root, study_instance_uid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/series", response_model=list[SeriesSummary])
def list_series(study_instance_uid: str | None = Query(default=None)) -> list[SeriesSummary]:
    return service.list_series(settings.dicom_root, study_instance_uid=study_instance_uid)


@router.get("/series/{series_instance_uid}", response_model=SeriesDetail)
def get_series(series_instance_uid: str) -> SeriesDetail:
    try:
        return service.get_series(settings.dicom_root, series_instance_uid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/series/{series_instance_uid}/instances", response_model=list[InstanceSummary])
def list_instances(series_instance_uid: str) -> list[InstanceSummary]:
    try:
        return service.list_instances(settings.dicom_root, series_instance_uid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
