import argparse
import json
from pathlib import Path
from typing import Any

import pydicom
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence


DEFAULT_TARGET = Path(r"query tool/idc-data/remind/ReMIND-001")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read DICOM metadata from a file or a whole directory tree."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=str(DEFAULT_TARGET),
        help="Path to a DICOM file or directory.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional JSON output file. Recommended for large folders.",
    )
    parser.add_argument(
        "--all-files",
        action="store_true",
        help="Try all files instead of only *.dcm.",
    )
    parser.add_argument(
        "--max-print",
        type=int,
        default=3,
        help="How many file metadata blocks to print to the console.",
    )
    return parser.parse_args()


def discover_files(target: Path, all_files: bool) -> list[Path]:
    if target.is_file():
        return [target]

    if not target.is_dir():
        raise FileNotFoundError(f"Path does not exist: {target}")

    pattern = "*" if all_files else "*.dcm"
    return sorted(path for path in target.rglob(pattern) if path.is_file())


def simplify_value(value: Any) -> Any:
    if isinstance(value, Sequence):
        return [dataset_to_dict(item) for item in value]
    if isinstance(value, Dataset):
        return dataset_to_dict(value)
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [simplify_value(item) for item in value]
    return str(value)


def element_to_dict(element: DataElement) -> dict[str, Any]:
    return {
        "tag": str(element.tag),
        "keyword": element.keyword or "",
        "name": element.name,
        "vr": element.VR,
        "value": simplify_value(element.value),
    }


def dataset_to_dict(dataset: Dataset) -> dict[str, Any]:
    return {
        (element.keyword or str(element.tag)): element_to_dict(element)
        for element in dataset
    }


def read_metadata(file_path: Path) -> dict[str, Any]:
    dataset = pydicom.dcmread(file_path, stop_before_pixels=True, force=True)
    return {
        "file_path": str(file_path),
        "study_instance_uid": str(getattr(dataset, "StudyInstanceUID", "") or ""),
        "series_instance_uid": str(getattr(dataset, "SeriesInstanceUID", "") or ""),
        "sop_instance_uid": str(getattr(dataset, "SOPInstanceUID", "") or ""),
        "modality": str(getattr(dataset, "Modality", "") or ""),
        "study_date": str(getattr(dataset, "StudyDate", "") or ""),
        "series_description": str(getattr(dataset, "SeriesDescription", "") or ""),
        "metadata": dataset_to_dict(dataset),
    }


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    studies = {item["study_instance_uid"] for item in items if item["study_instance_uid"]}
    series = {item["series_instance_uid"] for item in items if item["series_instance_uid"]}
    modalities = sorted({item["modality"] for item in items if item["modality"]})
    return {
        "file_count": len(items),
        "study_count": len(studies),
        "series_count": len(series),
        "modalities": modalities,
    }


def build_tag_overview(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {"common_tags": {}, "varying_tags": {}}

    tag_values: dict[str, list[Any]] = {}
    tag_meta: dict[str, dict[str, Any]] = {}

    for item in items:
        for tag_key, tag_info in item["metadata"].items():
            tag_values.setdefault(tag_key, []).append(tag_info.get("value"))
            tag_meta.setdefault(
                tag_key,
                {
                    "tag": tag_info.get("tag"),
                    "keyword": tag_info.get("keyword"),
                    "name": tag_info.get("name"),
                    "vr": tag_info.get("vr"),
                },
            )

    common_tags: dict[str, Any] = {}
    varying_tags: dict[str, Any] = {}

    for tag_key, values in tag_values.items():
        unique_values: list[Any] = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)

        tag_payload = {
            **tag_meta[tag_key],
            "unique_value_count": len(unique_values),
            "sample_values": unique_values[:10],
        }

        if len(unique_values) == 1:
            common_tags[tag_key] = {
                **tag_payload,
                "value": unique_values[0],
            }
        else:
            varying_tags[tag_key] = tag_payload

    return {
        "common_tags": common_tags,
        "varying_tags": varying_tags,
    }


def main() -> None:
    args = parse_args()
    target = Path(args.target)
    files = discover_files(target, all_files=args.all_files)

    print(f"Target: {target}")
    print(f"Files found: {len(files)}")

    if not files:
        print("No candidate files found.")
        raise SystemExit(1)

    items: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []

    for file_path in files:
        try:
            items.append(read_metadata(file_path))
        except Exception as exc:
            failed.append({"file_path": str(file_path), "error": str(exc)})

    summary = build_summary(items)
    tag_overview = build_tag_overview(items)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))

    print("\n=== COMMON TAGS (sample) ===")
    print(json.dumps(dict(list(tag_overview["common_tags"].items())[:20]), indent=2, ensure_ascii=False))

    print("\n=== VARYING TAGS ===")
    print(json.dumps(tag_overview["varying_tags"], indent=2, ensure_ascii=False))

    for item in items[: max(args.max_print, 0)]:
        print("\n=== FILE METADATA ===")
        print(item["file_path"])
        print(json.dumps(item["metadata"], indent=2, ensure_ascii=False))

    payload = {
        "target": str(target),
        "summary": summary,
        "tag_overview": tag_overview,
        "files": items,
        "failed_files": failed,
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nFull metadata written to: {output_path}")
    elif len(items) > max(args.max_print, 0):
        print(
            "\nLarge result set detected. Use --output metadata.json to save the full metadata dump."
        )

    if failed:
        print(f"\nFailed to read {len(failed)} files.")


if __name__ == "__main__":
    main()
