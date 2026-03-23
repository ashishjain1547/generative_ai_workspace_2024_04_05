import re
import csv
from decimal import Decimal
import pdfplumber

PDF_PATH = "./AccountStatement_41135518208_23032026_unlocked.pdf"
CSV_PATH = "post_date_balance.csv"

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
MONEY_RE = re.compile(r"^[\d,]+(?:\.\d{2})?$")

def normalize_amount(s: str) -> str:
    """Convert Indian-formatted amounts like 39,10,619.00 to plain number string."""
    if s is None:
        return ""
    s = s.strip()
    s = s.replace(",", "")
    return s

def try_extract_rows_from_table(table):
    """
    table is a list of rows from pdfplumber extract_table().
    We expect columns:
    Post Date | Value Date | Details | Ref No/Cheque | Debit | Credit | Balance
    """
    extracted = []

    for row in table:
        if not row or len(row) < 7:
            continue

        post_date = (row[0] or "").strip()
        balance = (row[6] or "").strip()

        # Skip header rows and empty rows
        if post_date == "Post Date" or not DATE_RE.match(post_date):
            continue

        # Balance can sometimes be blank on non-transaction rows like rate change
        if balance and MONEY_RE.match(balance.replace(",", "")):
            extracted.append({
                "post_date": post_date,
                "balance": normalize_amount(balance),
            })

    return extracted

def main():
    all_rows = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # Try table extraction first
            table = page.extract_table()

            if table:
                rows = try_extract_rows_from_table(table)
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
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["post_date", "balance"])
        writer.writeheader()
        writer.writerows(unique_rows)

    print(f"Saved {len(unique_rows)} rows to {CSV_PATH}")

if __name__ == "__main__":
    main()
