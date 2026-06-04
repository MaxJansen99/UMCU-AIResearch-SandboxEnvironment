import json
import threading
import time
from time import perf_counter

from app.services.query_service import QueryService


def collect_and_save_stats(query_service: QueryService, stats_file: str) -> None:
    print("Collecting DICOM header stats from PACS...")
    started_at = perf_counter()
    stats, total_series, total_instances = query_service.collect_all_stats()
    payload = {
        "stats": stats,
        "total_series": total_series,
        "total_instances": total_instances,
        "elapsed_seconds": perf_counter() - started_at,
        "timestamp": time.time(),
    }
    with open(stats_file, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
    print(f"Stats collected and saved to {stats_file} in {payload['elapsed_seconds']:.2f}s")


def start_periodic_collection(query_service: QueryService, stats_file: str, interval_hours: int = 24) -> None:
    def collect_forever() -> None:
        while True:
            time.sleep(interval_hours * 3600)
            collect_and_save_stats(query_service, stats_file)

    threading.Thread(target=collect_forever, daemon=True).start()
