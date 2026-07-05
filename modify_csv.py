import csv
import sys
import os
import re
import argparse
from datetime import datetime

NEW_COL_NAME    = "NAME OF THE SHARESHOLDERS"
NEW_COL_ADDRESS = "ADDRESS OF THE SHAREHOLDERS"
NEW_COL_STATE   = "State"
NEW_COL_PIN     = "PIN"
NEW_COL_FOLIO   = "Folio Number of Security"

REQUIRED = {NEW_COL_NAME, NEW_COL_ADDRESS, NEW_COL_FOLIO}

OUT_FIELDS = [
    "folio_id", "name", "address", "pin_code",
    "net_dividend", "date_of_transfer",
]

DATE_RE   = re.compile(r'\d{2}-[A-Za-z]{3}-\d{4}')
AMOUNT_RE = re.compile(r'\d+\.\d+')


def parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    for fmt in ("%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def normalize_headers(fieldnames):
    """Collapse embedded newlines and repeated spaces from header names."""
    return {k: " ".join(k.replace("\n", " ").split()) for k in (fieldnames or [])}


def parse_folio_and_amount(folio_raw, amount_raw):
    """
    Two layouts observed across file versions:

    Layout A — folio col populated, amount col = "AMOUNT  DATE":
      folio: "CUMMIN30177416379489"
      amount: "36.00  06-Oct-2023"

    Layout B — folio col empty, overflow packed into amount col:
      folio: ""
      amount: "CUMM000000000A020320  1575.00  06-Oct-2023"

    PIN always comes from the dedicated PIN column (caller's responsibility).
    Returns: (folio_id, amount_str, date_str)
    """
    folio_raw  = (folio_raw  or "").strip()
    amount_raw = (amount_raw or "").strip()

    folio_id = ""
    amt_str  = ""
    date_str = ""

    if folio_raw:
        # Layout A: folio is clean in its own cell
        folio_id = folio_raw
        src      = amount_raw
    else:
        # Layout B: folio, amount, and date are all packed into the amount cell
        tokens = amount_raw.split()
        if tokens and re.match(r'^[A-Za-z]', tokens[0]):
            folio_id = tokens[0]
            tokens   = tokens[1:]
        src = " ".join(tokens)

    m = AMOUNT_RE.search(src)
    if m:
        amt_str = m.group()
    m = DATE_RE.search(src)
    if m:
        date_str = m.group()

    return folio_id, amt_str, date_str


# ── Core transform ────────────────────────────────────────────────────────────

def transform_single_file(input_path, output_path, missing_name_writer):
    # First pass: read and normalize headers
    with open(input_path, newline="", encoding="utf-8-sig") as infile:
        reader     = csv.DictReader(infile)
        raw_fields = reader.fieldnames or []
        header_map = normalize_headers(raw_fields)   # raw_key -> clean_key
        clean_set  = set(header_map.values())

    # Amount column may be "Amount" or "Amount Due (in ..." depending on the file version
    col_amount = next((v for v in clean_set if v.lower().startswith("amount")), None)

    missing = REQUIRED - clean_set
    if missing or not col_amount:
        reason = f"Missing columns: {missing}" if missing else "No Amount column found"
        print(f"[ERROR] Skipping {os.path.basename(input_path)}. {reason}")
        return 0, 0

    filename            = os.path.basename(input_path)
    rows_processed      = 0
    missing_names_count = 0

    with open(input_path, newline="", encoding="utf-8-sig") as infile, \
         open(output_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=OUT_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for row in reader:
            # Normalize keys so embedded newlines in headers don't break lookups
            clean_row = {header_map.get(k, k): v for k, v in row.items()}

            name = (clean_row.get(NEW_COL_NAME) or "").strip()

            if not name:
                missing_names_count += 1
                row_data_str = ", ".join(f"{k}: {v}" for k, v in clean_row.items() if v)
                missing_name_writer.writerow({
                    "source_file":  filename,
                    "row_index":    reader.line_num,
                    "raw_row_data": row_data_str,
                })

            folio_id, amount, date_str = parse_folio_and_amount(
                clean_row.get(NEW_COL_FOLIO),
                clean_row.get(col_amount),
            )

            address_parts = [
                " ".join((clean_row.get(NEW_COL_ADDRESS) or "").strip().replace("\n", " ").split()),
                (clean_row.get(NEW_COL_STATE) or "").strip(),
            ]

            writer.writerow({
                "folio_id":         folio_id,
                "name":             name,
                "address":          ", ".join(p for p in address_parts if p),
                "pin_code":         (clean_row.get(NEW_COL_PIN) or "").strip(),
                "net_dividend":     amount,
                "date_of_transfer": parse_date(date_str),
            })
            rows_processed += 1

    return rows_processed, missing_names_count


def main():
    parser = argparse.ArgumentParser(
        description="Batch transform a folder of raw folio CSVs into the normalized target folder."
    )
    parser.add_argument("input_dir",  help="Path to the directory containing raw input CSV files")
    parser.add_argument("-o", "--output-dir", required=True,
                        help="Path to the directory where transformed CSVs will be written")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"[ERROR] Input directory not found: {args.input_dir}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[INFO] Reading from : {args.input_dir}")
    print(f"[INFO] Outputting to: {args.output_dir}\n" + "-" * 50)

    total_files_processed = 0
    total_missing_names   = 0

    log_file_path = os.path.join(args.output_dir, "missing_names_log.csv")

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        log_fields = ["source_file", "row_index", "raw_row_data"]
        log_writer = csv.DictWriter(log_file, fieldnames=log_fields, quoting=csv.QUOTE_ALL)
        log_writer.writeheader()

        for file in sorted(os.listdir(args.input_dir)):
            if not file.lower().endswith(".csv") or file == "missing_names_log.csv":
                continue

            input_file_path  = os.path.join(args.input_dir, file)
            base, ext        = os.path.splitext(file)
            output_file_path = os.path.join(args.output_dir, f"{base}_transformed{ext}")

            print(f"[PROCESSING] {file}...")
            row_count, missing_count = transform_single_file(
                input_file_path, output_file_path, log_writer
            )

            suffix = f"  (WARN: {missing_count} missing names)" if missing_count else ""
            print(f"             -> {row_count} rows extracted.{suffix}")

            total_files_processed += 1
            total_missing_names   += missing_count

    print("-" * 50)
    print(f"[DONE] Transformed {total_files_processed} file(s) into {args.output_dir}")
    if total_missing_names:
        print(f"[WARN] {total_missing_names} row(s) with missing name — see {log_file_path}")


if __name__ == "__main__":
    main()
