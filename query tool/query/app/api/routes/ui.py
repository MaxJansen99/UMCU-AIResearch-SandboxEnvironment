from fastapi import APIRouter

from app.services.dicom_query_service import OPERATORS


router = APIRouter(prefix="/ui", tags=["ui"])


@router.get("/config")
def get_ui_config() -> dict[str, list[str]]:
    return {
        "operators": list(OPERATORS.keys()),
        "filter_tags": [
            "StudyDate",
            "StudyDescription",
            "SeriesDescription",
            "Modality",
            "BodyPartExamined",
            "InstanceNumber",
        ],
        "stats_tags": [
            "Modality",
            "BodyPartExamined",
            "StudyDate",
            "StudyDescription",
            "SeriesDescription",
        ],
    }
