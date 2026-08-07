"""
JSON-based pipeline checkpoint / resume state.

File: logs/pipeline_state.json

Schema:
{
  "version": 1,
  "run_id": "20260807_123456",
  "last_updated": "2026-08-07T12:34:56",
  "phases": {
    "<phase>": {
      "status": "completed" | "in_progress" | "not_started",
      "processed": ["file1.pdf", ...],
      "failed": {"file2.pdf": "error message", ...},
      "skipped": {"file3.pdf": "reason", ...}
    }
  }
}
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from config import STATE_FILE, LOGS_DIR


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _empty_phase_state() -> dict:
    return {
        "status": "not_started",
        "processed": [],
        "failed": {},
        "skipped": {},
    }


def init_state(run_id: str | None = None) -> dict:
    """Create a fresh state dictionary."""
    if run_id is None:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "version": 1,
        "run_id": run_id,
        "last_updated": _now_iso(),
        "phases": {
            "ocr": _empty_phase_state(),
            "ingest": _empty_phase_state(),
            "similarity": _empty_phase_state(),
        },
    }


def load_state() -> dict | None:
    """Load existing checkpoint, or None if missing/corrupted."""
    if not STATE_FILE.exists():
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        # basic validation
        if "version" in state and "phases" in state:
            return state
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_state(state: dict) -> None:
    """Atomically write state to disk (write temp → rename).

    Handles OneDrive file locks by retrying with backoff, then falling
    back to delete-then-rename if os.replace() continues to fail.
    """
    state["last_updated"] = _now_iso()
    os.makedirs(str(LOGS_DIR), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        suffix=".json", prefix="checkpoint_", dir=str(LOGS_DIR)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        # Try atomic replace with retries (OneDrive sometimes holds a lock)
        _atomic_replace(tmp_path, str(STATE_FILE))

    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _atomic_replace(src: str, dst: str, retries: int = 5, delay: float = 0.1) -> None:
    """Replace dst with src atomically.  Retries on PermissionError (e.g. OneDrive lock)."""
    import time as _time
    last_err = None
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:
            last_err = e
            if attempt < retries - 1:
                _time.sleep(delay * (2 ** attempt))  # 0.1, 0.2, 0.4, 0.8, 1.6s
    # Final fallback: delete target first, then rename
    try:
        Path(dst).unlink(missing_ok=True)
        os.rename(src, dst)
    except OSError:
        raise last_err or OSError(f"Could not replace {dst}")


def clear_state() -> None:
    """Remove the checkpoint file (fresh start)."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def mark_done(state: dict, phase: str, filename: str) -> None:
    """Record a file as successfully processed."""
    p = state["phases"][phase]
    if filename not in p["processed"]:
        p["processed"].append(filename)
    # remove from failed/skipped if was previously there
    p["failed"].pop(filename, None)
    p["skipped"].pop(filename, None)


def mark_failed(state: dict, phase: str, filename: str, error: str) -> None:
    """Record a file failure with error message."""
    p = state["phases"][phase]
    p["failed"][filename] = error


def mark_skipped(state: dict, phase: str, filename: str, reason: str) -> None:
    """Record a file that was intentionally skipped (e.g. text-based PDF)."""
    p = state["phases"][phase]
    p["skipped"][filename] = reason


def set_phase_status(state: dict, phase: str, status: str) -> None:
    """Set phase status to 'not_started', 'in_progress', or 'completed'."""
    state["phases"][phase]["status"] = status


def get_pending(
    state: dict, phase: str, all_files: list[str], *, skip_failed: bool = False
) -> list[str]:
    """Return files that still need processing for a given phase.

    Excludes already-processed files. Optionally excludes previously-failed files.
    Files in 'skipped' are also excluded (they were intentionally skipped).
    """
    p = state["phases"][phase]
    done = set(p["processed"])
    if skip_failed:
        done.update(p["failed"].keys())
    done.update(p["skipped"].keys())
    return [f for f in all_files if f not in done]
