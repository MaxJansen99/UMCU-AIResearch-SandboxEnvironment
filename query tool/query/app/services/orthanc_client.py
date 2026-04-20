from typing import Any

import requests


class OrthancClient:
    def __init__(self, base_url: str, auth: tuple[str, str] | None = None, timeout: int = 30) -> None:
        if not base_url:
            raise ValueError("Orthanc/PACS URL is required.")
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout

    def get(self, path: str) -> Any:
        response = requests.get(f"{self.base_url}{path}", auth=self.auth, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        response = requests.post(f"{self.base_url}{path}", auth=self.auth, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        return self.get("/statistics")

    def find_series(self, query: dict[str, Any] | None = None) -> list[str]:
        result = self.post("/tools/find", {"Level": "Series", "Query": query or {}})
        return result if isinstance(result, list) else []

    def get_series(self, series_id: str) -> dict[str, Any]:
        return self.get(f"/series/{series_id}")

    def get_study(self, study_id: str) -> dict[str, Any]:
        return self.get(f"/studies/{study_id}")

    def get_series_instances(self, series_id: str) -> list[Any]:
        result = self.get(f"/series/{series_id}/instances")
        return result if isinstance(result, list) else []

    def get_instance_tags(self, instance_id: str) -> dict[str, Any]:
        result = self.get(f"/instances/{instance_id}/tags")
        return result if isinstance(result, dict) else {}

    def get_instance_file(self, instance_id: str) -> bytes:
        response = requests.get(f"{self.base_url}/instances/{instance_id}/file", auth=self.auth, timeout=self.timeout)
        response.raise_for_status()
        return response.content
