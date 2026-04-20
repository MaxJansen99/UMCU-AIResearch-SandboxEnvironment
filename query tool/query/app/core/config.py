import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    pacs_url: str = os.environ.get("QUERY_PACS_URL", "")
    pacs_user: str = os.environ.get("QUERY_PACS_USER", "orthanc")
    pacs_password: str = os.environ.get("QUERY_PACS_PASSWORD", "orthanc")
    host: str = os.environ.get("QUERY_HOST", "0.0.0.0")
    port: int = int(os.environ.get("QUERY_PORT", "8000"))
    tls_enabled: bool = os.environ.get("QUERY_TLS", "false").lower() in {"1", "true", "yes"}
    tls_cert: str = os.environ.get("QUERY_TLS_CERT", "/certs/server.crt")
    tls_key: str = os.environ.get("QUERY_TLS_KEY", "/certs/server.key")
    tls_ca: str = os.environ.get("QUERY_TLS_CA", "")
    stats_file: str = os.environ.get("QUERY_STATS_FILE", "stats.json")
    collect_stats_on_startup: bool = os.environ.get("QUERY_COLLECT_STATS_ON_STARTUP", "true").lower() in {
        "1",
        "true",
        "yes",
    }
    db_host: str = os.environ.get("DB_HOST", "localhost")
    db_port: int = int(os.environ.get("DB_PORT", "5432"))
    db_name: str = os.environ.get("DB_NAME", "dicom_query")
    db_user: str = os.environ.get("DB_USER", "dicom_query")
    db_password: str = os.environ.get("DB_PASSWORD", "dicom_query")

    @property
    def auth(self) -> tuple[str, str] | None:
        if self.pacs_user and self.pacs_password:
            return self.pacs_user, self.pacs_password
        return None

    @property
    def db_connection_info(self) -> dict[str, str | int]:
        return {
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
        }


settings = Settings()
