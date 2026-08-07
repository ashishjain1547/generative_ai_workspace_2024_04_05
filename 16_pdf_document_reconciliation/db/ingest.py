"""
Thin wrapper � legacy entry point for standalone ingest only.
Streamlines the old db/ingest.py by importing shared modules.
"""

import os
import sqlite3
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config import DB_PATH, DB_DIR, LOGS_DIR
from checkpoint import init_state, set_phase_status, save_state, load_state
from logging_utils import init_perf_log, save_perf_log
from db import create_db, load_vector_extension, init_vector_extension, rotate_db_file
from ingest import run_ingest_phase
from similarity import compute_top_k_matches, print_similarity_summary


def main():
    print("=" * 60)
    print("LEGACY: Standalone Ingest + Similarity")
    print("=" * 60)

    os.makedirs(str(LOGS_DIR), exist_ok=True)
    os.makedirs(str(DB_DIR), exist_ok=True)

    rotate_db_file(fresh=True)

    state = load_state() or init_state()
    set_phase_status(state, "ingest", "in_progress")
    save_state(state)

    conn = sqlite3.connect(str(DB_PATH))
    create_db(conn)
    load_vector_extension(conn)
    init_vector_extension(conn)

    perf_f, perf_writer, perf_path = init_perf_log(LOGS_DIR)
    try:
        run_ingest_phase(conn, perf_writer, DB_PATH, state)
    except (KeyboardInterrupt, SystemExit):
        save_perf_log(perf_f, perf_path)
        conn.close()
        raise
    save_perf_log(perf_f, perf_path)
    set_phase_status(state, "ingest", "completed")
    save_state(state)

    print("\n-- Similarity Matrix Preview --")
    result = compute_top_k_matches(conn)
    print_similarity_summary(result)

    conn.close()
    print("\n[ALL DONE]")


if __name__ == "__main__":
    main()