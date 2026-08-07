"""
Thin wrapper - legacy entry point for standalone OCR only.
Uses the original legacy paths: input/AI Contract test -> output/image_to_text.
"""

import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config import (
    LEGACY_OCR_INPUT_DIR, LEGACY_OCR_OUTPUT_DIR, LOGS_DIR,
)
from checkpoint import init_state, set_phase_status, save_state, load_state
from logging_utils import init_ocr_log, save_ocr_log
from ocr import run_ocr_phase


def main():
    print("=" * 60)
    print("LEGACY: Standalone OCR (AI Contract test)")
    print("=" * 60)

    os.makedirs(LEGACY_OCR_OUTPUT_DIR, exist_ok=True)

    state = load_state() or init_state()
    set_phase_status(state, "ocr", "in_progress")
    save_state(state)

    ocr_f, ocr_writer, ocr_log_path = init_ocr_log(LOGS_DIR)
    try:
        run_ocr_phase(
            LEGACY_OCR_INPUT_DIR, LEGACY_OCR_OUTPUT_DIR,
            ocr_writer, ocr_f, state,
            gpu=False,
        )
    except (KeyboardInterrupt, SystemExit):
        save_ocr_log(ocr_f, ocr_log_path)
        raise
    save_ocr_log(ocr_f, ocr_log_path)

    set_phase_status(state, "ocr", "completed")
    save_state(state)
    print("[DONE]")


if __name__ == "__main__":
    main()