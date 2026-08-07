"""
PaddleOCR worker — runs inside the `paddleocr` conda environment.

Usage (from parent pipeline):
    paddle_ocr_env/python.exe paddle_ocr_worker.py
        --input-dir INPUT_DIR --output-dir OUTPUT_DIR
        [--file-list FILE_LIST] [--gpu] [--lang en]

For each PDF, renders pages at 300 DPI, runs PaddleOCR, writes a .txt file,
and prints one JSON progress line to stdout.

Requires (in the paddleocr env): paddleocr, paddlepaddle-gpu, PyMuPDF, numpy
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ── Ensure CUDA / cuDNN DLLs are discoverable ─────────────────────
# When this script is run via a direct python.exe path (not `conda activate`),
# the conda env's Library\bin is not on PATH, so PaddlePaddle cannot find
# cudnn64_8.dll, cudart64_110.dll, etc.
#
# We use SetDllDirectoryW (the Win32 API) rather than os.add_dll_directory()
# because PaddlePaddle's C++ dynamic_loader uses LoadLibrary without the
# LOAD_LIBRARY_SEARCH_USER_DIRS flag, and modifying os.environ["PATH"] from
# within Python only affects subprocesses — not the current process's DLL
# search order.  SetDllDirectoryW reliably adds to the process search path.
import ctypes as _ctypes
_CONDA_ENV_DIR = Path(sys.executable).resolve().parent.parent  # paddleocr/
_LIB_BIN = _CONDA_ENV_DIR / "Library" / "bin"
if _LIB_BIN.exists():
    _ctypes.WinDLL("kernel32", use_last_error=True).SetDllDirectoryW(
        str(_LIB_BIN)
    )

import fitz  # PyMuPDF
import numpy as np
from paddleocr import PaddleOCR


def process_pdf(pdf_path: Path, input_dir: Path, output_dir: Path, ocr: PaddleOCR) -> dict:
    """OCR a single PDF with PaddleOCR. Returns a status dict.

    Output .txt is written to a mirrored subdirectory under output_dir
    so that input/A/B/doc.pdf → output/A/B/doc.txt.
    """
    t_start = time.perf_counter()
    doc = fitz.open(str(pdf_path))
    pages = doc.page_count
    all_lines = []

    for page_num in range(pages):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        if pix.n == 4:
            img = img[:, :, :3]

        result = ocr.ocr(img, cls=True)
        if result and result[0]:
            for line_info in result[0]:
                text = line_info[1][0]
                all_lines.append(text)

    doc.close()
    elapsed = time.perf_counter() - t_start
    text = "\n".join(all_lines)

    # ── Compute relative path for mirrored output ───────────────
    try:
        rel = pdf_path.resolve().relative_to(input_dir.resolve())
    except ValueError:
        rel = pdf_path.relative_to(input_dir)
    rel_str = str(rel).replace("\\", "/")
    rel_parent = str(Path(rel_str).parent)

    if rel_parent and rel_parent != ".":
        out_subdir = output_dir / rel_parent
        os.makedirs(out_subdir, exist_ok=True)
        out_path = out_subdir / f"{pdf_path.stem}.txt"
    else:
        out_path = output_dir / f"{pdf_path.stem}.txt"

    out_path.write_text(text, encoding="utf-8")

    return {
        "status": "ok",
        "pages": pages,
        "chars": len(text),
        "elapsed": round(elapsed, 4),
        "output": out_path.name,
        "file": rel_str,  # report relative path so parent can identify the file uniquely
    }


def main():
    parser = argparse.ArgumentParser(description="PaddleOCR PDF Worker")
    parser.add_argument("--input-dir", required=True, help="Directory with PDF files")
    parser.add_argument("--output-dir", required=True, help="Directory for .txt output")
    parser.add_argument("--file-list", default=None,
                        help="Path to a file listing PDF filenames to process (one per line)")
    parser.add_argument("--gpu", action="store_true", help="Use CUDA GPU")
    parser.add_argument("--lang", default="en", help="OCR language (default: en)")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # ── Determine files to process ────────────────────────────────
    if args.file_list and os.path.exists(args.file_list):
        with open(args.file_list, "r", encoding="utf-8") as f:
            pdf_paths = [
                input_dir / line.strip()
                for line in f if line.strip()
            ]
    else:
        pdf_paths = sorted(input_dir.glob("*.pdf"))

    pdf_paths = [p for p in pdf_paths if p.exists() and p.suffix.lower() == ".pdf"]

    # ── Load PaddleOCR ────────────────────────────────────────────
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang=args.lang,
        use_gpu=args.gpu,
        show_log=False,
    )

    # ── Process each PDF, report JSON per file to stdout ──────────
    for pdf_path in pdf_paths:
        # Compute relative path for reporting
        try:
            rel = pdf_path.resolve().relative_to(input_dir.resolve())
        except ValueError:
            rel = pdf_path.relative_to(input_dir)
        rel_str = str(rel).replace("\\", "/")

        try:
            info = process_pdf(pdf_path, input_dir, output_dir, ocr)
            # 'file' is already set by process_pdf to the relative path
        except Exception as e:
            info = {
                "file": rel_str,
                "status": "error",
                "error": str(e),
            }
        print(json.dumps(info), flush=True)


if __name__ == "__main__":
    main()
