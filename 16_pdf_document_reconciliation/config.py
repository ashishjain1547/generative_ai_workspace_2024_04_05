"""
Shared configuration, paths, constants, and CLI argument parsing.
"""

import argparse
import shutil
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
TXT_OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
DB_DIR = BASE_DIR / "db"
DB_PATH = DB_DIR / "pdf_reconciliation.db"
STATE_FILE = LOGS_DIR / "pipeline_state.json"
TRACKING_CSV_PATH = LOGS_DIR / "processing_tracker.csv"

# ── Tracking CSV column names ─────────────────────────────────────────
TRACKING_COLUMNS = [
    "SNO",
    "TIMESTAMP_PROCESSED",
    "RELATIVE_PATH_WINDOWS",
    "RELATIVE_PATH_LINUX",
    "OCR_REQUIRED",
    "OCR_DONE",
    "ENCODING_AND_INGESTION_DONE",
    "#_OF_FILE_PROCESSED",
]

# ── Legacy OCR paths (used by image_to_text/ocr.py wrapper) ───────────
LEGACY_OCR_INPUT_DIR = BASE_DIR / "input" / "AI Contract test"
LEGACY_OCR_OUTPUT_DIR = BASE_DIR / "output" / "image_to_text"

# ── Model & DB constants ──────────────────────────────────────────────
MODEL_NAME = "BAAI/bge-m3"
TABLE_NAME = "pdf_document_reconciliation"
VECTOR_COLUMN = "embedding"
EMBEDDING_DIM = 1024

# ── OCR heuristic ─────────────────────────────────────────────────────
MIN_TEXT_CHARS_PER_PAGE = 100  # avg chars/page below this → image-based

# ── Ingest truncation ─────────────────────────────────────────────────
MAX_TEXT_CHARS = 32000  # ~8192 tokens for BGE-M3

# ── Similarity ────────────────────────────────────────────────────────
TOP_K = 10  # top-N matches per document in report

# ── OCR engine defaults ───────────────────────────────────────────────
OCR_ENGINE = "easyocr"  # "easyocr" | "paddle"
OCR_LANGUAGES = ["en"]
PADDLE_CONDA_ENV_NAME = "paddleocr"


def detect_gpu() -> bool:
    """Auto-detect if a CUDA-capable GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        pass
    return shutil.which("nvidia-smi") is not None


def compute_relative_paths(pdf_path: Path) -> tuple[str, str, str]:
    """Compute three relative-path variants for a PDF under INPUT_DIR.

    Returns:
        rel_win:    Windows-style path relative to BASE_DIR  (for CSV)
        rel_linux:  Linux-style path relative to BASE_DIR    (for CSV key + DB doc name)
        rel_input:  Linux-style path relative to INPUT_DIR   (for mirrored output)
    """
    try:
        rel_base = pdf_path.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        # Fallback: compute from parts if resolve() yields different drives
        rel_base = pdf_path.relative_to(BASE_DIR)
    rel_win = str(rel_base).replace("/", "\\")
    rel_linux = str(rel_base).replace("\\", "/")
    rel_input = str(rel_base.relative_to("input")).replace("\\", "/")
    return rel_win, rel_linux, rel_input


def find_paddle_python() -> str | None:
    """Locate python.exe in the paddleocr conda env. Returns None if not found."""
    candidates = [
        Path.home() / "AppData" / "Local" / "anaconda3" / "envs" / PADDLE_CONDA_ENV_NAME / "python.exe",
        Path.home() / "anaconda3" / "envs" / PADDLE_CONDA_ENV_NAME / "python.exe",
        Path.home() / "miniconda3" / "envs" / PADDLE_CONDA_ENV_NAME / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def parse_args():
    """Parse CLI arguments for the pipeline."""
    parser = argparse.ArgumentParser(
        description="PDF Document Reconciliation Pipeline"
    )
    parser.add_argument(
        "--phases",
        default="ocr,ingest,similarity",
        help="Comma-separated phases to run: ocr,ingest,similarity (default: all)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="(Default) Resume from tracking CSV; skip already-processed files.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force fresh start: rotate DB, clear checkpoint, reprocess all files "
             "(appends new rows to tracking CSV with incremented #_OF_FILE_PROCESSED).",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=0,
        help="Halt after N consecutive failures (0 = no limit)",
    )
    parser.add_argument(
        "--skip-failed",
        action="store_true",
        help="On resume, skip previously-failed files instead of retrying them",
    )
    parser.add_argument(
        "--ocr-engine",
        choices=["easyocr", "paddle"],
        default=OCR_ENGINE,
        help=f"OCR engine to use (default: {OCR_ENGINE})",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Force enable CUDA GPU (default: auto-detect)",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Force disable GPU (default: auto-detect)",
    )
    parser.add_argument(
        "--paddle-python",
        default=None,
        help="Path to python.exe in paddleocr conda env (auto-detected if not set)",
    )
    return parser.parse_args()
