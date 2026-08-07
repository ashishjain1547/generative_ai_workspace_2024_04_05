"""
Processing-tracker CSV — per-file source of truth for resume decisions.

File: logs/processing_tracker.csv
Columns: SNO, TIMESTAMP_PROCESSED, RELATIVE_PATH_WINDOWS,
         RELATIVE_PATH_LINUX, OCR_REQUIRED, OCR_DONE,
         ENCODING_AND_INGESTION_DONE, #_OF_FILE_PROCESSED

This is an append-only log.  Each file processed in a run gets one or more
rows (one per phase completed).  On resume the latest row per unique
RELATIVE_PATH_LINUX determines what still needs work.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from config import TRACKING_COLUMNS


def _now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_tracker(csv_path: Path) -> list[dict[str, str]]:
    """Read the entire tracking CSV into a list of dicts.

    Returns an empty list if the file does not exist or is empty.
    """
    if not csv_path.exists():
        return []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def append_tracker_row(csv_path: Path, row: dict[str, Any]) -> None:
    """Append a single row to the tracking CSV.

    Creates the file with a header row if it does not already exist.
    All values are coerced to strings before writing.
    """
    file_exists = csv_path.exists()
    os.makedirs(str(csv_path.parent), exist_ok=True)

    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TRACKING_COLUMNS)
        if not file_exists:
            writer.writeheader()
        # Coerce every value to str so csv.DictWriter doesn't complain
        safe_row = {k: str(v) for k, v in row.items()}
        writer.writerow(safe_row)


def get_latest_row(
    csv_path: Path, rel_path_linux: str
) -> dict[str, str] | None:
    """Return the most recent row (highest SNO) for a given relative path.

    Returns None if the file has never been tracked.
    """
    rows = load_tracker(csv_path)
    matching = [r for r in rows if r.get("RELATIVE_PATH_LINUX") == rel_path_linux]
    if not matching:
        return None
    # Highest SNO is the latest
    matching.sort(key=lambda r: int(r.get("SNO", 0)), reverse=True)
    return matching[0]


def get_next_sno(csv_path: Path) -> int:
    """Return the next SNO value (max existing + 1, or 1 if empty)."""
    rows = load_tracker(csv_path)
    if not rows:
        return 1
    max_sno = max(int(r.get("SNO", 0)) for r in rows)
    return max_sno + 1


def get_previous_count(csv_path: Path, rel_path_linux: str) -> int:
    """Count how many rows already exist for this file.

    Used to compute the next #_OF_FILE_PROCESSED value.
    """
    rows = load_tracker(csv_path)
    return sum(1 for r in rows if r.get("RELATIVE_PATH_LINUX") == rel_path_linux)


def _latest_status(csv_path: Path, rel_path_linux: str, column: str) -> str:
    """Return the value of *column* in the latest row for a file, or ''."""
    row = get_latest_row(csv_path, rel_path_linux)
    if row is None:
        return ""
    return row.get(column, "")


def is_ocr_done(csv_path: Path, rel_path_linux: str) -> bool:
    """True if the latest row for this file shows OCR is complete or N/A."""
    status = _latest_status(csv_path, rel_path_linux, "OCR_DONE")
    return status in ("YES", "NA")


def is_ingest_done(csv_path: Path, rel_path_linux: str) -> bool:
    """True if the latest row for this file shows ingest is complete or N/A."""
    status = _latest_status(csv_path, rel_path_linux, "ENCODING_AND_INGESTION_DONE")
    return status in ("YES", "NA")


# ── File identity tuple used by build_pending_lists ───────────────
# (full_path: Path, rel_win: str, rel_linux: str, rel_input: str)
FileInfo = tuple[Path, str, str, str]


def build_pending_lists(
    csv_path: Path,
    all_files: list[FileInfo],
) -> tuple[list[FileInfo], list[FileInfo]]:
    """Split the master file list into OCR-pending and ingest-pending.

    A file needs OCR if its latest row does NOT have OCR_DONE ∈ {YES, NA}.
    A file needs ingest if its latest row does NOT have
    ENCODING_AND_INGESTION_DONE ∈ {YES, NA}.

    Returns (pending_ocr, pending_ingest) — each is a subset of *all_files*.
    """
    pending_ocr: list[FileInfo] = []
    pending_ingest: list[FileInfo] = []

    for fi in all_files:
        _full, _win, linux, _inp = fi
        if not is_ocr_done(csv_path, linux):
            pending_ocr.append(fi)
        if not is_ingest_done(csv_path, linux):
            pending_ingest.append(fi)

    return pending_ocr, pending_ingest


# ── Convenience: build a complete row and append it ───────────────

def write_phase_row(
    csv_path: Path,
    rel_win: str,
    rel_linux: str,
    ocr_required: str,
    ocr_done: str,
    ingest_done: str,
) -> None:
    """Compute SNO and #_OF_FILE_PROCESSED, then append a tracker row.

    Typical caller usage:
        # After OCR succeeds:
        write_phase_row(csv_path, rel_win, rel_linux, "YES", "YES", "NO")
        # After ingest succeeds:
        write_phase_row(csv_path, rel_win, rel_linux, "YES", "YES", "YES")
    """
    sno = get_next_sno(csv_path)
    prev = get_previous_count(csv_path, rel_linux)
    append_tracker_row(csv_path, {
        "SNO": sno,
        "TIMESTAMP_PROCESSED": _now_ts(),
        "RELATIVE_PATH_WINDOWS": rel_win,
        "RELATIVE_PATH_LINUX": rel_linux,
        "OCR_REQUIRED": ocr_required,
        "OCR_DONE": ocr_done,
        "ENCODING_AND_INGESTION_DONE": ingest_done,
        "#_OF_FILE_PROCESSED": prev + 1,
    })
