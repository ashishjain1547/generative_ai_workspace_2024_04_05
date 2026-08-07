"""
OCR phase — detect image-based PDFs and extract text via EasyOCR.
With per-file error handling, checkpoint support, and crash-safe logging.
"""

import os
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import fitz  # PyMuPDF
import easyocr

from config import MIN_TEXT_CHARS_PER_PAGE, OCR_LANGUAGES, find_paddle_python
from checkpoint import mark_done, mark_failed, mark_skipped, save_state
from logging_utils import log_ocr_row
from tracking import write_phase_row


def is_image_based_pdf(pdf_path: Path) -> bool:
    """Return True if the PDF has very little extractable text (scanned/images)."""
    try:
        doc = fitz.open(str(pdf_path))
        total_chars = sum(len(page.get_text().strip()) for page in doc)
        pages = doc.page_count
        doc.close()
        return (total_chars / max(pages, 1)) < MIN_TEXT_CHARS_PER_PAGE
    except Exception:
        return False  # treat unreadable as potentially image-based


def extract_text_with_ocr(pdf_path: Path, reader: easyocr.Reader) -> str:
    """Render each page to an image, run EasyOCR, return combined text."""
    doc = fitz.open(str(pdf_path))
    all_lines = []
    for page_num, page in enumerate(doc, 1):
        pix = page.get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            img = img[:, :, :3]

        result = reader.readtext(img)
        all_lines.extend(item[1] for item in result)
        print(f"    page {page_num}: {len(all_lines)} lines total")

    doc.close()
    return "\n".join(all_lines)


def run_ocr_phase(
    input_dir: Path,
    output_dir: Path,
    ocr_writer: Any,
    ocr_f: Any,
    state: dict,
    *,
    gpu: bool = False,
    max_consecutive_failures: int = 0,
    pending_files: list[tuple[Path, str, str, str]] | None = None,
    engine: str = "easyocr",
    paddle_python: str | None = None,
    tracker_csv_path: Path | None = None,
) -> int:
    """Run OCR on image-based PDFs and save extracted text as .txt files.

    pending_files: list of (full_path, rel_win, rel_linux, rel_to_input).
        rel_to_input is used to mirror the input subdirectory structure
        under output_dir.

    engine='easyocr': uses EasyOCR in-process (all dependencies in current env).
    engine='paddle':  shells out to PaddleOCR in its own conda environment.

    Returns the number of OCR-processed files.
    """
    print("=" * 60)
    engine_label = "EasyOCR" if engine == "easyocr" else "PaddleOCR (subprocess)"
    print(f"PHASE 1: OCR — {engine_label}")
    print("=" * 60)

    os.makedirs(output_dir, exist_ok=True)

    # ── Discover files ────────────────────────────────────────────
    if pending_files is not None:
        pdf_files = sorted(pending_files, key=lambda t: t[2])  # sort by rel_linux
    else:
        # Legacy flat scan (kept for backward compat)
        raw = sorted(input_dir.glob("*.pdf"))
        pdf_files = [(p, p.name, p.name, p.name) for p in raw]
    print(f"Found {len(pdf_files)} PDF(s) in: {input_dir}\n")

    if engine == "paddle":
        return _run_paddle_ocr_subprocess(
            input_dir, output_dir, pdf_files,
            gpu=gpu,
            state=state,
            ocr_writer=ocr_writer,
            ocr_f=ocr_f,
            max_consecutive_failures=max_consecutive_failures,
            paddle_python=paddle_python,
            tracker_csv_path=tracker_csv_path,
        )

    # ── EasyOCR path ──────────────────────────────────────────────
    try:
        reader = easyocr.Reader(OCR_LANGUAGES, gpu=gpu)
    except Exception as e:
        print(f"[FATAL] EasyOCR failed to load: {e}")
        raise
    print(f"[OK] EasyOCR loaded (gpu={gpu})\n")

    ocr_count = 0
    consecutive_failures = 0

    for sno, (pdf_path, rel_win, rel_linux, rel_to_input) in enumerate(pdf_files, 1):
        filename = pdf_path.name
        print(f"Checking: {filename} … ", end="", flush=True)

        # ── Build mirrored output path ───────────────────────────
        rel_parent = str(Path(rel_to_input).parent)
        if rel_parent and rel_parent != ".":
            out_subdir = output_dir / rel_parent
            os.makedirs(out_subdir, exist_ok=True)
            out_path = out_subdir / f"{pdf_path.stem}.txt"
        else:
            out_path = output_dir / f"{pdf_path.stem}.txt"

        try:
            if not is_image_based_pdf(pdf_path):
                print("TEXT-based — skipping")
                mark_skipped(state, "ocr", rel_linux, "text-based PDF")
                save_state(state)
                if tracker_csv_path:
                    write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                    "NO", "NA", "NO")
                consecutive_failures = 0
                continue

            print("IMAGE-based — running OCR")
            t_start = time.perf_counter()
            text = extract_text_with_ocr(pdf_path, reader)
            elapsed = time.perf_counter() - t_start

            if not text.strip():
                print(f"  ⚠ No text extracted — recording as failure")
                mark_failed(state, "ocr", rel_linux, "empty OCR output")
                save_state(state)
                log_ocr_row(ocr_writer, sno, rel_linux, 0, elapsed, 0, "")
                ocr_f.flush()
                if tracker_csv_path:
                    write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                    "YES", "NO", "NO")
                consecutive_failures += 1
                if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                    print(f"[HALT] {max_consecutive_failures} consecutive failures reached.")
                    raise SystemExit(1)
                continue

            out_path.write_text(text, encoding="utf-8")

            doc = fitz.open(str(pdf_path))
            pages = doc.page_count
            doc.close()

            ocr_count += 1
            log_ocr_row(ocr_writer, sno, rel_linux, pages, elapsed,
                        len(text), out_path.name)
            ocr_f.flush()

            mark_done(state, "ocr", rel_linux)
            save_state(state)
            if tracker_csv_path:
                write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                "YES", "YES", "NO")
            consecutive_failures = 0
            print(f"  ✓ saved → {out_path.name}  ({len(text)} chars, {elapsed:.2f}s)\n")

        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Saving checkpoint before exit...")
            save_state(state)
            raise
        except Exception as e:
            print(f"\n  ✗ FAILED: {e}")
            mark_failed(state, "ocr", rel_linux, str(e))
            save_state(state)
            log_ocr_row(ocr_writer, sno, rel_linux, 0, 0, 0, f"ERROR: {e}")
            ocr_f.flush()
            if tracker_csv_path:
                write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                "YES", "NO", "NO")
            consecutive_failures += 1
            if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                print(f"[HALT] {max_consecutive_failures} consecutive failures reached.")
                raise SystemExit(1)

    print(f"[DONE] OCR phase — {ocr_count} file(s) processed.\n")
    return ocr_count


# ═══════════════════════════════════════════════════════════════════════
#  PaddleOCR subprocess backend
# ═══════════════════════════════════════════════════════════════════════

def _run_paddle_ocr_subprocess(
    input_dir: Path,
    output_dir: Path,
    pdf_files: list[tuple[Path, str, str, str]],
    gpu: bool,
    state: dict,
    ocr_writer: Any,
    ocr_f: Any,
    *,
    max_consecutive_failures: int = 0,
    paddle_python: str | None = None,
    tracker_csv_path: Path | None = None,
) -> int:
    """Run PaddleOCR via subprocess in its own conda environment.

    pdf_files: list of (full_path, rel_win, rel_linux, rel_to_input).

    Launches paddle_ocr_worker.py which processes all PDFs and reports
    JSON progress per file on stdout.  This function reads stdout
    line-by-line, checkpointing after each file.
    """

    # ── Build lookup: rel_to_input → (pdf_path, rel_win, rel_linux) ─
    file_lookup: dict[str, tuple[Path, str, str]] = {}

    # ── Filter: image-based only ──────────────────────────────────
    image_based: list[tuple[Path, str, str, str]] = []
    for pdf_path, rel_win, rel_linux, rel_to_input in pdf_files:
        if is_image_based_pdf(pdf_path):
            image_based.append((pdf_path, rel_win, rel_linux, rel_to_input))
            file_lookup[rel_to_input] = (pdf_path, rel_win, rel_linux)
        else:
            print(f"TEXT-based — skipping: {pdf_path.name}")
            mark_skipped(state, "ocr", rel_linux, "text-based PDF")
            save_state(state)
            if tracker_csv_path:
                write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                "NO", "NA", "NO")
    pdf_files = image_based

    if not pdf_files:
        print("[INFO] No image-based PDFs to process with PaddleOCR.")
        return 0

    # ── Resolve Paddle Python ─────────────────────────────────────
    if paddle_python is None:
        paddle_python = find_paddle_python()
    if paddle_python is None or not Path(paddle_python).exists():
        raise RuntimeError(
            "PaddleOCR Python not found. Install the 'paddleocr' conda env "
            "or pass --paddle-python PATH."
        )

    worker_script = Path(__file__).resolve().parent / "paddle_ocr_worker.py"
    if not worker_script.exists():
        raise RuntimeError(f"Worker script not found: {worker_script}")

    # ── Write file list for the worker ─────────────────────────────
    file_list_path = output_dir / "_paddle_batch_files.txt"
    # Write relative paths (rel_to_input) so the worker can resolve
    # files in subdirectories under input_dir
    file_list_path.write_text(
        "\n".join(ri for (_p, _w, _l, ri) in pdf_files),
        encoding="utf-8",
    )

    # ── Build and launch subprocess ───────────────────────────────
    cmd = [
        paddle_python, str(worker_script),
        "--input-dir", str(input_dir),
        "--output-dir", str(output_dir),
        "--file-list", str(file_list_path),
    ]
    if gpu:
        cmd.append("--gpu")

    # ── Ensure child process inherits Library\bin on PATH ─────────
    # paddle_ocr_worker.py needs CUDA/cuDNN DLLs from the conda env;
    # they live in <env>/Library/bin which is only on PATH after
    # `conda activate`.  We add it to the child's environment here.
    env = os.environ.copy()
    paddle_env_dir = Path(paddle_python).resolve().parent.parent  # paddleocr/
    lib_bin = str(paddle_env_dir / "Library" / "bin")
    if os.path.isdir(lib_bin):
        env["PATH"] = lib_bin + os.pathsep + env.get("PATH", "")

    print(f"[INFO] Launching PaddleOCR worker ({len(pdf_files)} files) ...")
    print(f"[CMD] {' '.join(cmd)}\n")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    ocr_count = 0
    consecutive_failures = 0

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARN] Non-JSON worker output: {line}")
                continue

            filename = entry.get("file", "unknown")
            # Look up the full FileInfo via rel_to_input (now reported by worker)
            lookup = file_lookup.get(filename)
            if lookup is None:
                # Fallback: try matching by bare filename
                for key, val in file_lookup.items():
                    if Path(key).name == filename:
                        lookup = val
                        filename = key  # use full rel path for consistency
                        break
            if lookup:
                _pdf_path, rel_win, rel_linux = lookup
            else:
                rel_win = filename
                rel_linux = filename

            if entry.get("status") == "ok":
                ocr_count += 1
                log_ocr_row(
                    ocr_writer, ocr_count, rel_linux,
                    entry.get("pages", 0),
                    entry.get("elapsed", 0),
                    entry.get("chars", 0),
                    entry.get("output", ""),
                )
                ocr_f.flush()
                mark_done(state, "ocr", rel_linux)
                save_state(state)
                if tracker_csv_path:
                    write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                    "YES", "YES", "NO")
                consecutive_failures = 0
                print(f"  ✓ saved → {entry.get('output', '?')}  "
                      f"({entry.get('chars', 0)} chars, {entry.get('elapsed', 0):.2f}s)")

            else:
                error_msg = entry.get("error", "unknown error")
                mark_failed(state, "ocr", rel_linux, error_msg)
                save_state(state)
                log_ocr_row(ocr_writer, ocr_count + 1, rel_linux, 0, 0, 0,
                            f"ERROR: {error_msg}")
                ocr_f.flush()
                if tracker_csv_path:
                    write_phase_row(tracker_csv_path, rel_win, rel_linux,
                                    "YES", "NO", "NO")
                consecutive_failures += 1
                print(f"  ✗ FAILED: {rel_linux} — {error_msg}")

                if max_consecutive_failures and consecutive_failures >= max_consecutive_failures:
                    print(f"[HALT] {max_consecutive_failures} consecutive failures.")
                    proc.terminate()
                    raise SystemExit(1)

        proc.wait(timeout=30)

    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Terminating PaddleOCR worker ...")
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        save_state(state)
        raise

    finally:
        stderr_output = proc.stderr.read()
        if stderr_output.strip():
            print(f"\n[PADDLE stderr]:\n{stderr_output[:2000]}")

    if proc.returncode != 0:
        print(f"[WARN] PaddleOCR worker exited with code {proc.returncode}")

    # ── Clean up temp file list ───────────────────────────────────
    try:
        file_list_path.unlink(missing_ok=True)
    except OSError:
        pass

    print(f"\n[DONE] OCR phase — {ocr_count} file(s) processed.\n")
    return ocr_count
