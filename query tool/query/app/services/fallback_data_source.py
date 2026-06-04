from typing import Any


class FallbackDataSource:
    def __init__(self, primary: Any, fallback: Any) -> None:
        self.primary = primary
        self.fallback = fallback
        self.active = primary
        self.base_url = getattr(primary, "base_url", "primary")
        self.last_error: str | None = None

    def health(self) -> dict[str, Any]:
        try:
            result = self.active.health()
        except Exception as exc:
            if self.active is self.fallback:
                raise
            self._switch_to_fallback(exc)
            result = self.fallback.health()
        return {**result, **self.source_info()}

    def find_series(self, query: dict[str, Any] | None = None) -> list[str]:
        try:
            result = self.active.find_series(query)
        except Exception as exc:
            if self.active is self.fallback:
                raise
            self._switch_to_fallback(exc)
            result = self.fallback.find_series(query)
        return result

    def get_series(self, series_id: str) -> dict[str, Any]:
        return self.active.get_series(series_id)

    def get_study(self, study_id: str) -> dict[str, Any]:
        return self.active.get_study(study_id)

    def get_series_instances(self, series_id: str) -> list[Any]:
        return self.active.get_series_instances(series_id)

    def get_instance_tags(self, instance_id: str) -> dict[str, Any]:
        return self.active.get_instance_tags(instance_id)

    def get_instance_file(self, instance_id: str) -> bytes:
        return self.active.get_instance_file(instance_id)

    @property
    def source_name(self) -> str:
        if self.active is self.fallback:
            return "csv"
        return "orthanc"

    def source_info(self) -> dict[str, Any]:
        return {
            "ActiveSource": self.source_name,
            "FallbackActive": self.active is self.fallback,
            "PrimarySource": getattr(self.primary, "source_name", "orthanc"),
            "FallbackSource": getattr(self.fallback, "source_name", "csv"),
            "LastSourceError": self.last_error,
        }

    def _switch_to_fallback(self, exc: Exception) -> None:
        self.last_error = str(exc)
        print(f"Primary datasource failed, switching to CSV fallback: {self.last_error}")
        self.active = self.fallback
        self.base_url = getattr(self.fallback, "base_url", "fallback")
