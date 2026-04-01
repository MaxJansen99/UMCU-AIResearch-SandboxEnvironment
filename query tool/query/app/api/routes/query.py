from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.query import QueryRequest, QueryResponse
from app.services.dicom_query_service import DicomQueryService


router = APIRouter(tags=["query"])
service = DicomQueryService()


@router.post("/query", response_model=QueryResponse)
def run_query(payload: QueryRequest) -> QueryResponse:
    try:
        return service.run_query(payload, default_root=settings.dicom_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
