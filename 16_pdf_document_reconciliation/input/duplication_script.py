import os
import shutil
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # 16_pdf_document_reconciliation
SRC_DIR = BASE_DIR / "input" / "AI Contract test"
DST_DIR = BASE_DIR / "input" / "10K"
COPIES_PER_FILE = 1000  # 1K

def main():
    files = sorted(SRC_DIR.iterdir())

    print(f"Found {len(files)} file(s) in source directory.")
    print(f"Creating {COPIES_PER_FILE} copies of each → {len(files) * COPIES_PER_FILE} total files.")
    print("-" * 60)

    for src_path in files:
        if not src_path.is_file():
            continue

        stem = src_path.stem      # filename without extension
        suffix = src_path.suffix  # .pdf, .txt, etc.

        for i in range(1, COPIES_PER_FILE + 1):
            dst_name = f"{stem}_copy_{i}{suffix}"
            dst_path = DST_DIR / dst_name
            shutil.copy2(src_path, dst_path)

        print(f"  ✓ {src_path.name} → {COPIES_PER_FILE} copies done")

    print("-" * 60)
    print("All copies created successfully.")

if __name__ == "__main__":
    main()
