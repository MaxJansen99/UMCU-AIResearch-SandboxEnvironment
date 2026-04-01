from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(tags=["health"])

@router.get("/health")
def healthcheck() -> dict[str, str | bool]:
    return {
        "ok": True,
        "service": "dicom-query",
        "default_root": settings.dicom_root,
    }
