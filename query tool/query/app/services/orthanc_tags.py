from typing import Any


def normalize_orthanc_dicom_tags(dicom_tags: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(dicom_tags, dict):
        return {}

    normalized: dict[str, Any] = {}
    for tag_key, entry in dicom_tags.items():
        if isinstance(entry, dict):
            name = entry.get("Name")
            value = entry.get("Value")
            if name is not None:
                normalized[name] = normalize_orthanc_value(value)
            else:
                normalized[tag_key] = normalize_orthanc_dicom_tags(entry)
        else:
            normalized[tag_key] = entry
    return normalized


def normalize_orthanc_value(value: Any) -> Any:
    if isinstance(value, dict):
        return normalize_orthanc_dicom_tags(value)
    if isinstance(value, list):
        return [normalize_orthanc_value(item) for item in value]
    return value


def safe_get(meta: dict[str, Any], key: str) -> Any:
    main_tags = meta.get("MainDicomTags", {})
    if key in main_tags:
        return main_tags[key]
    return meta.get(key)


def safe_get_full(meta: dict[str, Any], key: str) -> Any:
    main_tags = meta.get("MainDicomTags", {})
    if key in main_tags:
        return main_tags[key]

    dicom_tags = meta.get("DicomTags", {})
    if isinstance(dicom_tags, dict):
        if key in dicom_tags:
            return dicom_tags[key]

        for entry in dicom_tags.values():
            if isinstance(entry, dict) and entry.get("Name") == key:
                return entry.get("Value")

    return meta.get(key)
