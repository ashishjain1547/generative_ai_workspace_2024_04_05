import os
import re
import csv
from decimal import Decimal
import pdfplumber

DATA_DIR = "./data"
DEBUG = True

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
MONEY_RE = re.compile(r"^[\d,]+(?:\.\d{2})?(?:\s*(?:DR|CR))?\s*$")


def find_latest_pdf(data_dir=DATA_DIR):
    """Return the path of the latest PDF and its YYYYMMDD date prefix from the filename."""
    pdf_files = [
        os.path.join(data_dir, f)
        for f in os.listdir(data_dir)
        if f.lower().endswith(".pdf")
    ]
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {data_dir}")

    # Sort by the 8-digit date (YYYYMMDD) in the filename, mtime as tiebreak
    def sort_key(path):
        m = re.search(r"\d{8}", os.path.basename(path))
        return (m.group(0) if m else "", os.path.getmtime(path))

    pdf_files.sort(key=sort_key)
    latest_pdf = pdf_files[-1]

    m = re.search(r"\d{8}", os.path.basename(latest_pdf))
    date_prefix = m.group(0) if m else ""

    return latest_pdf, date_prefix


def normalize_amount(s: str) -> str:
    """Convert Indian-formatted amounts like 39,10,619.00 DR to plain number string."""
    if s is None:
        return ""
    s = s.strip()
    # Strip DR/CR suffix (e.g., "37,66,411.00 DR" → "37,66,411.00")
    s = re.sub(r"\s*(?:DR|CR)\s*$", "", s, flags=re.IGNORECASE).strip()
    s = s.replace(",", "")
    return s

def try_extract_rows_from_table(table, debug=False):
    """
    table is a list of rows from pdfplumber extract_table().
    Post Date is the first column; Balance is the LAST monetary-value column.
    We scan backwards from the end of each row to find Balance,
    because pdfplumber may add empty trailing cells.
    """
    extracted = []
    debug_printed = 0

    for row in table:
        if not row or len(row) < 2:
            continue

        post_date = (row[0] or "").strip()

        # Skip header rows and empty rows
        if post_date == "Post Date" or not DATE_RE.match(post_date):
            continue

        # Scan backwards to find the last non-empty monetary value = Balance
        balance = ""
        for cell in reversed(row):
            val = (cell or "").strip()
            if val and MONEY_RE.match(val.replace(",", "")):
                balance = val
                break

        if debug and debug_printed < 5:
            print(f"  [DEBUG] Row (len={len(row)}): {row}")
            print(f"  [DEBUG]   → post_date='{post_date}', balance='{balance}'")
            debug_printed += 1

        # Balance can sometimes be blank on non-transaction rows like rate change
        if balance:
            extracted.append({
                "post_date": post_date,
                "balance": normalize_amount(balance),
            })

    return extracted

def main():
    pdf_path, date_prefix = find_latest_pdf()
    csv_path = os.path.join(DATA_DIR, f"{date_prefix}_post_date_balance.csv")

    print(f"Reading PDF: {pdf_path}")

    all_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Try table extraction first
            table = page.extract_table()

            if table:
                rows = try_extract_rows_from_table(table, debug=DEBUG)
                if rows:
                    all_rows.extend(rows)
                    continue

            # Fallback: line-by-line text parsing
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()

                # Transaction lines usually start with a date
                parts = line.split()
                if len(parts) < 2:
                    continue

                if DATE_RE.match(parts[0]):
                    # Balance is usually the last numeric field on the line
                    numeric_parts = [p for p in parts if MONEY_RE.match(p.replace(",", ""))]
                    if numeric_parts:
                        balance = normalize_amount(numeric_parts[-1])
                        all_rows.append({
                            "post_date": parts[0],
                            "balance": balance,
                        })

    # Remove duplicates while preserving order
    seen = set()
    unique_rows = []
    for r in all_rows:
        key = (r["post_date"], r["balance"])
        if key not in seen:
            seen.add(key)
            unique_rows.append(r)

    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["post_date", "balance"])
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"Saved {len(unique_rows)} rows to {csv_path}")

if __name__ == "__main__":
    main()
