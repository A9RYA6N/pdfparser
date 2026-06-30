import csv
import sys
import os
import argparse

COL_FIRST    = "Investor First \nName"
COL_MIDDLE   = "Investor Middle \nName"
COL_LAST     = "Investor Last \nName"
COL_F_FIRST  = "Father/Husband \nFirst Name"
COL_F_MIDDLE = "Father/Husband \nMiddle Name"
COL_F_LAST   = "Father/Husband Last \nName"
COL_ADDRESS  = "Address"
COL_DISTRICT = "District"
COL_STATE    = "State"
COL_COUNTRY  = "Country"
COL_PIN      = "Pin Code"
COL_FOLIO    = "Folio Number"
COL_AMOUNT   = "Amount \ntransferred"
COL_DATE     = "Date of event \n(date of declaration of \ndividend/redemption date of \npreference shares/date of \nmaturity of \nbonds/debentures/application \nmoney refundable/interest \nthereon\n(DD-MON-YYYY)"
COL_DP_ID    = "DP Id-Client Id-\nAccount Number"

REQUIRED = {
    COL_FIRST, COL_MIDDLE, COL_LAST,
    COL_F_FIRST, COL_F_MIDDLE, COL_F_LAST,
    COL_ADDRESS, COL_DISTRICT, COL_STATE, COL_COUNTRY, COL_PIN,
    COL_FOLIO, COL_AMOUNT, COL_DATE, COL_DP_ID,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def join_name(*parts):
    return " ".join(p.strip() for p in parts if p.strip())


def split_amount_and_date(amount_raw, date_raw):
    """
    Handles OCR-merged cells where amount and date end up in one column.
    Cases:
      1. amount_raw = "50.00  30-AUG-2010", date_raw = ""  → split on first whitespace
      2. date_raw   = "50.00  30-AUG-2010", amount_raw = "" → same split
      3. Both already separate and clean → use as-is
    """
    amount_raw = amount_raw.strip()
    date_raw   = date_raw.strip()

    if amount_raw and not date_raw and " " in amount_raw:
        parts = amount_raw.split(None, 1)
        return parts[0], parts[1]

    if date_raw and not amount_raw and " " in date_raw:
        parts = date_raw.split(None, 1)
        return parts[0], parts[1]

    return amount_raw, date_raw


def combine_address(row):
    parts = [
        row.get(COL_ADDRESS,  "").strip(),
        row.get(COL_DISTRICT, "").strip(),
        row.get(COL_STATE,    "").strip(),
        row.get(COL_COUNTRY,  "").strip(),
    ]
    return ", ".join(p for p in parts if p)


# ── Core transform ────────────────────────────────────────────────────────────

def transform_single_file(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])

        missing = REQUIRED - set(fieldnames)
        if missing:
            print(f"[ERROR] Skipping {os.path.basename(input_path)}. Missing columns: {missing}")
            return 0

    out_fields = [
        "folio_id", "dp_id", "name", "father_name",
        "address", "pin_code",
        "net_dividend", "date_of_transfer",
    ]

    with open(input_path, newline="", encoding="utf-8-sig") as infile, \
         open(output_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=out_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        rows_processed = 0
        for row in reader:
            net_dividend, date_of_transfer = split_amount_and_date(
                row.get(COL_AMOUNT, ""),
                row.get(COL_DATE,   ""),
            )

            writer.writerow({
                "folio_id":         row.get(COL_FOLIO, "").strip(),
                "dp_id":            row.get(COL_DP_ID, "").strip(),
                "name":             join_name(
                                        row.get(COL_FIRST,  ""),
                                        row.get(COL_MIDDLE, ""),
                                        row.get(COL_LAST,   ""),
                                    ),
                "father_name":      join_name(
                                        row.get(COL_F_FIRST,  ""),
                                        row.get(COL_F_MIDDLE, ""),
                                        row.get(COL_F_LAST,   ""),
                                    ),
                "address":          combine_address(row),
                "pin_code":         row.get(COL_PIN, "").strip(),
                "net_dividend":     net_dividend,
                "date_of_transfer": date_of_transfer,
            })
            rows_processed += 1

    return rows_processed


def main():
    parser = argparse.ArgumentParser(
        description="Batch transform a folder of raw folio CSVs into the normalized target folder."
    )
    parser.add_argument("input_dir", help="Path to the directory containing raw input CSV files")
    parser.add_argument("-o", "--output-dir", required=True, help="Path to the directory where transformed CSVs will be written")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"[ERROR] Input directory not found: {args.input_dir}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[INFO] Reading from : {args.input_dir}")
    print(f"[INFO] Outputting to: {args.output_dir}\n" + "-" * 50)

    total_files_processed = 0

    for file in os.listdir(args.input_dir):
        if file.lower().endswith(".csv"):
            input_file_path = os.path.join(args.input_dir, file)

            base, ext = os.path.splitext(file)
            output_file_path = os.path.join(args.output_dir, f"{base}_transformed{ext}")

            print(f"[PROCESSING] {file}...")
            row_count = transform_single_file(input_file_path, output_file_path)
            print(f"             -> Extracted {row_count} rows.")
            total_files_processed += 1

    print("-" * 50)
    print(f"[DONE] Successfully transformed {total_files_processed} files into {args.output_dir}")


if __name__ == "__main__":
    main()
