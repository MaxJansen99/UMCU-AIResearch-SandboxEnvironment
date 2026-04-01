import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    dicom_root: str = os.environ.get("DICOM_ROOT", "/data")
    query_host: str = os.environ.get("QUERY_HOST", "0.0.0.0")
    query_port: int = int(os.environ.get("QUERY_PORT", "8000"))


settings = Settings()
