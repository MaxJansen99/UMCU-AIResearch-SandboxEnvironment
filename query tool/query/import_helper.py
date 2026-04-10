#!/usr/bin/env python3
"""
Import DICOM files from a directory tree into Orthanc via REST API.
"""
import os
import sys
import time
from pathlib import Path

import requests

def import_dicom_dir(
    pacs_url: str,
    data_dir: str,
    username: str = "orthanc",
    password: str = "orthanc",
) -> None:
    """
    Walk data_dir and POST each .dcm file to Orthanc.
    """
    auth = (username, password)
    dcm_files = list(Path(data_dir).rglob("*.dcm"))
    
    if not dcm_files:
        print(f"No DICOM files found in {data_dir}")
        return
    
    print(f"Found {len(dcm_files)} DICOM files to import")
    
    imported = 0
    failed = 0
    
    for i, dcm_path in enumerate(dcm_files, 1):
        try:
            with open(dcm_path, "rb") as f:
                resp = requests.post(
                    f"{pacs_url.rstrip('/')}/instances",
                    auth=auth,
                    data=f.read(),
                    headers={"Content-Type": "application/dicom"},
                    timeout=30,
                )
                if resp.status_code in (200, 201, 409):  # 409 = already exists
                    imported += 1
                    if i % 50 == 0:
                        print(f"  [{i}/{len(dcm_files)}] imported {imported} files")
                else:
                    failed += 1
                    print(f"  [!] Failed to import {dcm_path.name}: {resp.status_code}")
        except Exception as e:
            failed += 1
            print(f"  [!] Error importing {dcm_path}: {e}")
    
    print(f"\nImport complete: {imported} imported, {failed} failed")
    
    # Verify by checking statistics
    try:
        stats = requests.get(f"{pacs_url.rstrip('/')}/statistics", auth=auth, timeout=30)
        if stats.status_code == 200:
            data = stats.json()
            print(f"PACS statistics: {data.get('CountInstances', 0)} instances, {data.get('CountSeries', 0)} series, {data.get('CountStudies', 0)} studies")
    except Exception as e:
        print(f"Could not fetch PACS statistics: {e}")

if __name__ == "__main__":
    pacs_url = os.environ.get("PACS_URL", "http://orthanc:8042")
    data_dir = os.environ.get("DATA_DIR", "/data")
    pacs_user = os.environ.get("PACS_USER", "orthanc")
    pacs_password = os.environ.get("PACS_PASSWORD", "orthanc")
    
    # Wait for PACS to be ready
    retries = 30
    for attempt in range(retries):
        try:
            requests.get(f"{pacs_url.rstrip('/')}/patients", auth=(pacs_user, pacs_password), timeout=5)
            print(f"Connected to PACS at {pacs_url}")
            break
        except Exception:
            if attempt < retries - 1:
                print(f"Waiting for PACS... ({attempt + 1}/{retries})")
                time.sleep(2)
            else:
                print(f"Failed to connect to PACS after {retries} attempts")
                sys.exit(1)
    
    import_dicom_dir(pacs_url, data_dir, pacs_user, pacs_password)
