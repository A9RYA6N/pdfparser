import csv
import sys
import os
import argparse

COL_FIRST       = "First Name"
COL_MIDDLE      = "Middle Name"
COL_LAST        = "Last Name"
COL_F_FIRST     = "Father/Husband First\nName"
COL_F_MIDDLE    = "Father/Husband\nMiddle Name"
COL_F_LAST      = "Father/Husband Last Name"
COL_ADDRESS     = "Address"
COL_COUNTRY     = "Country"
COL_STATE       = "State"
COL_DISTRICT    = "District"
COL_PIN         = "PINCode"
COL_FOLIO       = "Folio Number of\nSecurities"
COL_AMOUNT      = "Amount Due(in Rs.)"
COL_DATE        = "Proposed Date\nof transfer to\nIEPF (DD-MON-\nYYYY)"
 
REQUIRED = {
    COL_FIRST, COL_MIDDLE, COL_LAST,
    COL_F_FIRST, COL_F_MIDDLE, COL_F_LAST,
    COL_ADDRESS, COL_COUNTRY, COL_STATE, COL_DISTRICT, COL_PIN,
    COL_FOLIO, COL_AMOUNT, COL_DATE,
}
 
OUTPUT_DIR = "/Users/aryanburnwal/Documents/BL/pdfparser/created_tables/asian_paints/2012/todo"
 
# ── Helpers ───────────────────────────────────────────────────────────────────
 
def join_name(*parts):
    """Join name parts, skipping blanks, separated by a single space."""
    return " ".join(p.strip() for p in parts if p.strip())
 
 
def combine_address(row):
    """Merge Address, District, State, Country into one string."""
    parts = [
        row.get(COL_ADDRESS,  "").strip(),
        row.get(COL_DISTRICT, "").strip(),
        row.get(COL_STATE,    "").strip(),
        row.get(COL_COUNTRY,  "").strip(),
    ]
    return ", ".join(p for p in parts if p)
 
 
def split_amount_and_date(amount_raw, date_raw):
    """
    The date column often contains merged data: "4764.50 12-APR-2014"
    The amount column is usually empty in that case.
 
    Cases handled:
      1. date_raw = "4764.50 12-APR-2014", amount_raw = ""
         → net_dividend=4764.50, date_of_transfer=12-APR-2014
      2. amount_raw = "4764.50 12-APR-2014", date_raw = ""  (reverse merge)
         → same split logic
      3. Both already separate and clean → use as-is
      4. Only one value present → assign to the correct field
    """
    amount_raw = amount_raw.strip()
    date_raw   = date_raw.strip()
 
    # Case 1: date field has both values merged with a space
    if date_raw and " " in date_raw:
        parts = date_raw.split(None, 1)   # split on first whitespace only
        return parts[0], parts[1]
 
    # Case 2: amount field has both values merged (reverse situation)
    if amount_raw and " " in amount_raw:
        parts = amount_raw.split(None, 1)
        return parts[0], parts[1]
 
    # Case 3/4: values are already correct or one is empty
    return amount_raw, date_raw
 
 
# ── Core transform ────────────────────────────────────────────────────────────
 
def transform_single_file(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        fieldnames = [f for f in (reader.fieldnames or [])]
 
        missing = REQUIRED - set(fieldnames)
        if missing:
            print(f"[ERROR] Skipping {os.path.basename(input_path)}. Missing columns: {missing}")
            return 0
 
    out_fields = [
        "folio_id", "name", "father_name",
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
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"[ERROR] Input directory not found: {args.input_dir}")
        sys.exit(1)

    # Ensure targeted output workspace directories are generated securely
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[INFO] Reading from : {args.input_dir}")
    print(f"[INFO] Outputting to: {OUTPUT_DIR}\n" + "-"*50)

    total_files_processed = 0
    
    # Process every CSV found in the folder
    for file in os.listdir(args.input_dir):
        if file.lower().endswith(".csv"):
            input_file_path = os.path.join(args.input_dir, file)
            
            # Construct names for files safely matching output folder formats
            base, ext = os.path.splitext(file)
            output_file_path = os.path.join(OUTPUT_DIR, f"{base}_transformed{ext}")
            
            print(f"[PROCESSING] {file}...")
            row_count = transform_single_file(input_file_path, output_file_path)
            print(f"             -> Extracted {row_count} rows.")
            total_files_processed += 1

    print("-"*50)
    print(f"[DONE] Successfully transformed {total_files_processed} files into {OUTPUT_DIR}")


if __name__ == "__main__":
    main()