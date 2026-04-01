from pathlib import Path

from idc_index import IDCClient


STUDY_INSTANCE_UID = "1.3.6.1.4.1.14519.5.2.1.207544490797667703011829289839681390478"
DOWNLOAD_DIR = Path("/data")


def has_files(root: Path) -> bool:
    return any(path.is_file() for path in root.rglob("*"))


def main() -> None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    if has_files(DOWNLOAD_DIR):
        print("IDC data already present in /data, skipping download.")
        return

    IDCClient().download_from_selection(
        studyInstanceUID=STUDY_INSTANCE_UID,
        downloadDir=str(DOWNLOAD_DIR),
    )
    print(f"Downloaded study {STUDY_INSTANCE_UID} into {DOWNLOAD_DIR}")


if __name__ == "__main__":
    main()
