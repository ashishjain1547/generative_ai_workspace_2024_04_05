"""
CSV logging helpers for OCR processing and ingest performance.
"""

import csv
import os
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════
#  OCR processing log
# ═══════════════════════════════════════════════════════════════════════

OCR_LOG_COLUMNS = [
    "SNO", "FILENAME", "PAGES", "TIME_TAKEN_SEC",
    "CHARS_EXTRACTED", "OUTPUT_FILE",
]


def init_ocr_log(logs_dir: Path):
    """Create a timestamped CSV file for OCR processing logs.
    Returns (file_handle, csv_writer, file_path).
    """
    os.makedirs(str(logs_dir), exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = logs_dir / f"ocr_processing_log_{ts}.csv"
    f = open(str(path), "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(OCR_LOG_COLUMNS)
    return f, writer, path


def log_ocr_row(writer, sno: int, filename: str, pages: int,
                time_taken: float, chars: int, output_file: str):
    """Write a single OCR processing row to the CSV."""
    writer.writerow([
        sno, filename, pages,
        round(time_taken, 4), chars, output_file,
    ])


def save_ocr_log(f, path: Path):
    """Close the OCR log file."""
    f.close()
    print(f"[OK] OCR processing log saved → {path}")


# ═══════════════════════════════════════════════════════════════════════
#  Ingest performance log
# ═══════════════════════════════════════════════════════════════════════

PERF_LOG_COLUMNS = [
    "SNO", "FILENAME", "TIME_TAKEN", "DB_SIZE",
    "AVG_TIME_TAKEN_PER_FILE", "AVG_SPACE_TAKEN_PER_FILE",
]


def get_db_size_mb(db_path: Path) -> float:
    """Return the database file size in megabytes."""
    if not db_path.exists():
        return 0.0
    return os.path.getsize(str(db_path)) / (1024 * 1024)


def init_perf_log(logs_dir: Path):
    """Create a timestamped CSV file with headers.
    Returns (file_handle, csv_writer, file_path).
    """
    os.makedirs(str(logs_dir), exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = logs_dir / f"ingest_perf_report_{ts}.csv"
    f = open(str(path), "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(PERF_LOG_COLUMNS)
    return f, writer, path


def log_perf_row(writer, sno: int, filename: str, time_taken: float,
                 db_size_mb: float, avg_time: float, avg_space: float):
    """Write a single performance row to the CSV."""
    writer.writerow([
        sno, filename,
        round(time_taken, 4), round(db_size_mb, 4),
        round(avg_time, 4), round(avg_space, 4),
    ])


def save_perf_log(f, path: Path):
    """Close the CSV file."""
    f.close()
    print(f"[OK] Performance report saved → {path}")
