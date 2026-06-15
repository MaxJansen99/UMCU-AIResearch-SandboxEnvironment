from pathlib import Path
import re


SAFE_FOLDER_RE = re.compile(r"[^A-Za-z0-9_.-]+")


class RfsFolderConfig:
    def __init__(self, mapping_file: str | Path, require_explicit_mapping: bool = True) -> None:
        self.mapping_file = Path(mapping_file)
        self.require_explicit_mapping = require_explicit_mapping

    def folder_for_username(self, username: str) -> str:
        mappings = self._read_mappings()
        folder = mappings.get(username)
        if folder is None:
            if self.require_explicit_mapping:
                raise ValueError(f"No RFS folder mapping configured for user '{username}'.")
            folder = safe_folder_name(username)
        if Path(folder).is_absolute() or ".." in Path(folder).parts:
            raise ValueError(f"Unsafe RFS folder mapping for user '{username}'.")
        return folder

    def _read_mappings(self) -> dict[str, str]:
        if not self.mapping_file.is_file():
            return {}

        mappings: dict[str, str] = {}
        current_user: str | None = None
        for raw_line in self.mapping_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].rstrip()
            if not line.strip():
                continue

            if not raw_line.startswith((" ", "\t")) and line.endswith(":"):
                current_user = line[:-1].strip()
                continue

            if current_user and line.strip().startswith("folder:"):
                mappings[current_user] = line.split(":", 1)[1].strip().strip("'\"")

        return mappings


def safe_folder_name(value: str) -> str:
    value = value.strip()
    if not value:
        return "unknown_user"
    return SAFE_FOLDER_RE.sub("_", value)
