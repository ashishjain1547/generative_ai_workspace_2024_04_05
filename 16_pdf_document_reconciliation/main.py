"""
Pipeline orchestrator — ties together OCR, Ingest, and Similarity phases
with CLI-driven resume/checkpoint support.
"""

import os
import sqlite3
import sys
from pathlib import Path

from config import (
    INPUT_DIR, TXT_OUTPUT_DIR, LOGS_DIR, DB_DIR, DB_PATH,
    parse_args, TOP_K, detect_gpu, compute_relative_paths,
    TRACKING_CSV_PATH,
)
from checkpoint import (
    init_state, load_state, clear_state, save_state,
    set_phase_status,
)
from logging_utils import (
    init_ocr_log, save_ocr_log, init_perf_log, save_perf_log,
)
from db import rotate_db_file, load_vector_extension, create_db, init_vector_extension
from tracking import build_pending_lists
from ocr import run_ocr_phase
from ingest import run_ingest_phase
from similarity import run_similarity_phase


def main():
    args = parse_args()

    # ── Parse phases ──────────────────────────────────────────────
    selected_phases = {p.strip() for p in args.phases.split(",") if p.strip()}
    valid_phases = {"ocr", "ingest", "similarity"}
    unknown = selected_phases - valid_phases
    if unknown:
        print(f"[ERROR] Unknown phase(s): {unknown}. Valid: {valid_phases}")
        sys.exit(1)

    fresh = args.fresh  # resume is the default; --fresh to opt out

    # ── GPU auto-detection ───────────────────────────────────────
    if args.gpu:
        gpu = True
    elif args.no_gpu:
        gpu = False
    else:
        gpu = detect_gpu()
    print(f"[INFO] GPU: {'ON' if gpu else 'OFF'} "
          f"({'--gpu' if args.gpu else '--no-gpu' if args.no_gpu else 'auto-detected'})")

    max_fail = args.max_failures or 0
    skip_failed = args.skip_failed

    # ── Checkpoint ────────────────────────────────────────────────
    if fresh:
        clear_state()
        state = init_state()
    else:
        state = load_state() or init_state()

    # ── Master file discovery (recursive under input/) ────────────
    all_pdf_paths: list[Path] = []
    for pdf_path in sorted(INPUT_DIR.rglob("*.pdf")):
        if pdf_path.is_file() and pdf_path.suffix.lower() == ".pdf":
            all_pdf_paths.append(pdf_path)

    print(f"[INFO] Discovered {len(all_pdf_paths)} PDF(s) under: {INPUT_DIR}")

    # Build FileInfo tuples: (full_path, rel_win, rel_linux, rel_input)
    all_file_infos = []
    for p in all_pdf_paths:
        rel_win, rel_linux, rel_input = compute_relative_paths(p)
        all_file_infos.append((p, rel_win, rel_linux, rel_input))

    # ── DB rotation (only when running ingest fresh) ─────────────
    if "ingest" in selected_phases:
        rotate_db_file(fresh=fresh)

    # ── Phase 1: OCR ──────────────────────────────────────────────
    if "ocr" in selected_phases:
        set_phase_status(state, "ocr", "in_progress")
        save_state(state)

        # Determine pending files from tracking CSV
        if not fresh:
            pending_ocr_fi, _ = build_pending_lists(
                TRACKING_CSV_PATH, all_file_infos
            )
        else:
            pending_ocr_fi = all_file_infos

        # pending_ocr_fi is already list[(Path, str, str, str)] — pass directly
        pending_ocr = pending_ocr_fi

        print(f"[INFO] OCR pending: {len(pending_ocr)} file(s)")

        ocr_f, ocr_writer, ocr_log_path = init_ocr_log(LOGS_DIR)
        try:
            run_ocr_phase(
                INPUT_DIR, TXT_OUTPUT_DIR,
                ocr_writer, ocr_f, state,
                gpu=gpu,
                max_consecutive_failures=max_fail,
                pending_files=pending_ocr,
                engine=args.ocr_engine,
                paddle_python=args.paddle_python,
                tracker_csv_path=TRACKING_CSV_PATH,
            )
        except (SystemExit, KeyboardInterrupt):
            save_ocr_log(ocr_f, ocr_log_path)
            print("[INTERRUPTED] OCR phase halted. Use --resume to continue.")
            raise
        save_ocr_log(ocr_f, ocr_log_path)
        set_phase_status(state, "ocr", "completed")
        save_state(state)

    # ── Phase 2: Ingest ───────────────────────────────────────────
    if "ingest" in selected_phases:
        set_phase_status(state, "ingest", "in_progress")
        save_state(state)

        os.makedirs(str(DB_DIR), exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        create_db(conn)
        load_vector_extension(conn)
        init_vector_extension(conn)

        # Determine pending files from tracking CSV (re-read after OCR)
        if not fresh:
            _, pending_ingest_fi = build_pending_lists(
                TRACKING_CSV_PATH, all_file_infos
            )
        else:
            pending_ingest_fi = all_file_infos

        # Convert to (pdf_filename, rel_linux, rel_to_input) tuples
        pending_ingest: list[tuple[str, str, str]] = [
            (p.name, rl, ri) for (p, _w, rl, ri) in pending_ingest_fi
        ]

        print(f"[INFO] Ingest pending: {len(pending_ingest)} file(s)")

        perf_f, perf_writer, perf_path = init_perf_log(LOGS_DIR)
        try:
            run_ingest_phase(
                conn, perf_writer, DB_PATH, state,
                max_consecutive_failures=max_fail,
                pending_files=pending_ingest,
                tracker_csv_path=TRACKING_CSV_PATH,
            )
        except (SystemExit, KeyboardInterrupt):
            save_perf_log(perf_f, perf_path)
            conn.close()
            print("[INTERRUPTED] Ingest phase halted. Use --resume to continue.")
            raise
        save_perf_log(perf_f, perf_path)
        set_phase_status(state, "ingest", "completed")
        save_state(state)

    # ── Phase 3: Similarity ───────────────────────────────────────
    if "similarity" in selected_phases:
        needs_conn = "ingest" not in selected_phases
        if needs_conn:
            conn = sqlite3.connect(str(DB_PATH))
            create_db(conn)
            load_vector_extension(conn)
            init_vector_extension(conn)

        try:
            run_similarity_phase(conn, state, k=TOP_K)
        except (SystemExit, KeyboardInterrupt):
            if needs_conn:
                conn.close()
            raise

        if needs_conn:
            conn.close()

    # ── Cleanup ───────────────────────────────────────────────────
    if "ingest" in selected_phases or "similarity" in selected_phases:
        if "ingest" in selected_phases:
            conn.close()
        # else already closed above

    print("\n[ALL DONE] — Pipeline completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOPPED] Pipeline interrupted. Re-run to resume (default). "
              "Use --fresh for a full restart.")
        sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code if isinstance(e.code, int) else 1)
