"""
Ingest phase — read documents (PDF or OCR .txt), generate embeddings via
BAAI/bge-m3, store in SQLite with sqlite-vector.

Per-file error handling with checkpoint support.
"""

import os
import json
import time
import traceback
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer

from config import (
    INPUT_DIR, TXT_OUTPUT_DIR, MODEL_NAME, TABLE_NAME,
    VECTOR_COLUMN, MAX_TEXT_CHARS,
)
from checkpoint import mark_done, mark_failed, save_state
from logging_utils import get_db_size_mb, log_perf_row
from tracking import write_phase_row


def resolve_document_source(rel_to_input: str) -> tuple[str, bool]:
    """Prefer a .txt file (OCR output at mirrored path) over the PDF.

    rel_to_input is the linux-style path relative to INPUT_DIR,
    e.g. '20260807_1430/subfolder/doc.pdf'.
    Mirrored OCR output is at TXT_OUTPUT_DIR / '20260807_1430/subfolder/doc.txt'.
    """
    # Primary: mirrored OCR output
    txt_path = TXT_OUTPUT_DIR / rel_to_input
    txt_path = txt_path.with_suffix(".txt")
    if txt_path.exists():
        return str(txt_path), True
    # Fallback: raw PDF extraction via PyMuPDF
    pdf_path = INPUT_DIR / rel_to_input
    return str(pdf_path), False


def read_document_text(source_path: str, is_txt: bool) -> str:
    """Read text from a .txt file, or extract it from a PDF via PyMuPDF."""
    if is_txt:
        with open(source_path, encoding="utf-8") as f:
            return f.read().strip()

    doc = fitz.open(source_path)
    text_parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(text_parts).strip()


def run_ingest_phase(
    conn: Any,
    perf_writer: Any,
    db_path: Path,
    state: dict,
    *,
    max_consecutive_failures: int = 0,
    pending_files: list[tuple[str, str, str]] | None = None,
    tracker_csv_path: Path | None = None,
) -> None:
    """Read documents, generate embeddings, store in DB, log performance.

    pending_files: list of (pdf_filename, rel_linux, rel_to_input).
        - pdf_filename is the bare filename for display.
        - rel_linux is stored as document_name in the DB (unique across batches).
        - rel_to_input locates the source (OCR .txt or raw PDF).

    If pending_files is None, falls back to a flat scan of INPUT_DIR.

    Per-file error handling with checkpoint after each successful insert.
    """
    print("=" * 60)
    print("PHASE 2: INGEST (Embedding + Vector DB)")
    print("=" * 60)

    # ── Load model ────────────────────────────────────────────────
    try:
        model = SentenceTransformer(MODEL_NAME)
    except Exception as e:
        print(f"[FATAL] Failed to load model {MODEL_NAME}: {e}")
        raise
    print(f"[OK] Loaded model: {MODEL_NAME}")

    if pending_files is not None:
        file_tuples = sorted(pending_files, key=lambda t: t[1])  # sort by rel_linux
    else:
        # Legacy flat scan
        flat = sorted([
            f for f in os.listdir(str(INPUT_DIR))
            if f.lower().endswith(".pdf")
        ])
        file_tuples = [(f, f, f) for f in flat]
    total = len(file_tuples)
    print(f"[INFO] Found {total} file(s) to ingest.")

    cur = conn.cursor()
    cumulative_time = 0.0
    consecutive_failures = 0

    for idx, (pdf_filename, rel_linux, rel_to_input) in enumerate(file_tuples, 1):
        print(f"[{idx}/{total}] Processing: {pdf_filename} … ", end="", flush=True)

        try:
            # ── Resolve source ────────────────────────────────────
            source_path, is_txt = resolve_document_source(rel_to_input)
            source_label = "TXT" if is_txt else "PDF"
            print(f"(source: {source_label})")

            t_start = time.perf_counter()

            # ── Read document ─────────────────────────────────────
            full_text = read_document_text(source_path, is_txt)
            if not full_text:
                print(f"  ⚠ No text extracted — recording as failure")
                mark_failed(state, "ingest", rel_linux, "empty text")
                save_state(state)
                if tracker_csv_path:
                    write_phase_row(tracker_csv_path,
                                    rel_linux.replace("/", "\\"),
                                    rel_linux, "YES", "YES", "NO")
                consecutive_failures += 1
                if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                    print(f"[HALT] {max_consecutive_failures} consecutive failures.")
                    raise SystemExit(1)
                continue

            full_text = full_text[:MAX_TEXT_CHARS]

            # ── Generate embedding ────────────────────────────────
            embedding = model.encode(full_text, normalize_embeddings=True)
            emb_list = embedding.tolist()

            # ── Store ─────────────────────────────────────────────
            emb_json = json.dumps(emb_list)
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (document_name, embedding)
                VALUES (?, vector_as_f32(?))
                ON CONFLICT(document_name) DO UPDATE SET embedding=excluded.embedding
            """, (rel_linux, emb_json))
            conn.commit()

            elapsed = time.perf_counter() - t_start
            cumulative_time += elapsed
            avg_time = cumulative_time / idx
            db_size_mb = get_db_size_mb(db_path)
            avg_space = db_size_mb / idx

            log_perf_row(perf_writer, idx, rel_linux, elapsed,
                         db_size_mb, avg_time, avg_space)

            # ── Checkpoint ────────────────────────────────────────
            mark_done(state, "ingest", rel_linux)
            save_state(state)
            if tracker_csv_path:
                write_phase_row(tracker_csv_path,
                                rel_linux.replace("/", "\\"),
                                rel_linux, "YES", "YES", "YES")

            consecutive_failures = 0
            print(f"  ✓ Embedding stored (dim={len(emb_list)}) "
                  f"[{elapsed:.2f}s | DB: {db_size_mb:.2f} MB]")

        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Saving checkpoint before exit...")
            save_state(state)
            raise
        except Exception as e:
            print(f"\n  ✗ FAILED: {e}")
            mark_failed(state, "ingest", rel_linux, str(e))
            save_state(state)
            if tracker_csv_path:
                write_phase_row(tracker_csv_path,
                                rel_linux.replace("/", "\\"),
                                rel_linux, "YES", "YES", "NO")
            consecutive_failures += 1
            if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                print(f"[HALT] {max_consecutive_failures} consecutive failures.")
                raise SystemExit(1)

    print(f"\n[DONE] Ingested {total} document(s).")
