import csv
import sys
import os
import re
import argparse
from datetime import datetime

# Target structural output properties matching your model architecture specifications
OUT_FIELDS = [
    "folio_id", "name", "father_name", "address", "pin_code",
    "net_dividend", "date_of_transfer", "dp_id",
    "pan_no", "date_of_birth", "aadhar_no", "joint_holder_name"
]

# Robust regex patterns to parse shifted values or clean combined text anomalies
DATE_RE      = re.compile(r'\d{1,2}-[A-Za-z]{3}-\d{4}')
DIVIDEND_RE  = re.compile(r'\d+\.\d+')


def clean_field_string(val):
    """Strips cell whitespace and sanitizes baseline empty layout values."""
    s = " ".join((val or "").strip().split())
    return "" if s.upper() in ("NA", "0", ".", "") else s


def parse_date(raw_date_field):
    """Safely extracts a date sequence token and handles date format mapping to ISO YYYY-MM-DD."""
    val = (raw_date_field or "").strip()
    match = DATE_RE.search(val)
    if not match:
        return ""
    
    raw_date = match.group()
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d-%B-%Y", "%d-%B-%y"):
        try:
            return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw_date


def extract_net_dividend(investment_type, amount_transferred, proposed_date):
    """
    Safely isolates the clean numeric dividend value by combining all potential 
    leakage columns and stripping out target date strings to prevent day-of-month collisions.
    """
    # Pool text across all possible columns where the amount could reside
    combined_src = f"{investment_type or ''} {amount_transferred or ''} {proposed_date or ''}"
    
    # Meticulously strip the date segment out first (e.g., removes "02-JUL-2022")
    date_match = DATE_RE.search(combined_src)
    if date_match:
        combined_src = combined_src.replace(date_match.group(), "")
        
    # Extract the remaining numeric dividend characters
    amt_match = DIVIDEND_RE.search(combined_src)
    if amt_match:
        return amt_match.group()
        
    return ""


def transform_single_file(input_path, output_path, missing_name_writer):
    # Pass 1: Grab literal header list sequence to avoid dictionary construction drops
    with open(input_path, newline="", encoding="utf-8-sig") as infile:
        reader = csv.reader(infile)
        raw_fieldnames = [" ".join(h.split()) for h in next(reader, [])]

    # Map target columns layout position explicitly based on the new input headers configuration
    try:
        idx_f_name   = raw_fieldnames.index("Investor First Name")
        idx_m_name   = raw_fieldnames.index("Investor Middle Name")
        idx_l_name   = raw_fieldnames.index("Investor Last Name")
        idx_ff_name  = raw_fieldnames.index("Father/Husband First Name")
        idx_fm_name  = raw_fieldnames.index("Father/Husband Middle Name")
        idx_fl_name  = raw_fieldnames.index("Father/Husband Last Name")
        idx_address  = raw_fieldnames.index("Address")
        idx_country  = raw_fieldnames.index("Country")
        idx_state    = raw_fieldnames.index("State")
        idx_district = raw_fieldnames.index("District")
        idx_pin      = raw_fieldnames.index("Pin Code")
        idx_folio    = raw_fieldnames.index("Folio Number")
        idx_dpid     = raw_fieldnames.index("DP Id-Client Id- Account Number")
        idx_inv_type = raw_fieldnames.index("Investment Type")
        idx_amount   = raw_fieldnames.index("Amount transferred")
        idx_proposed = raw_fieldnames.index("Proposed Date of transfer to IEPF (DD-MON-YYYY)")
        idx_pan      = raw_fieldnames.index("PAN")
        idx_dob      = raw_fieldnames.index("Date of Birth")
        idx_aadhar   = raw_fieldnames.index("Aadhar Number")
        idx_joint    = raw_fieldnames.index("Joint Holder Name")
    except ValueError as e:
        print(f"[ERROR] Skipping {os.path.basename(input_path)}. Schema mismatch: {e}")
        return 0, 0

    filename = os.path.basename(input_path)
    rows_processed = 0
    missing_names_count = 0

    with open(input_path, newline="", encoding="utf-8-sig") as infile, \
         open(output_path, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.reader(infile)
        next(reader) # Skip header row

        writer = csv.DictWriter(outfile, fieldnames=OUT_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for row in reader:
            if len(row) < len(raw_fieldnames):
                row += [""] * (len(raw_fieldnames) - len(row))

            # 1. Process and cleanly stitch individual name components
            first_name  = clean_field_string(row[idx_f_name])
            middle_name = clean_field_string(row[idx_m_name])
            last_name   = clean_field_string(row[idx_l_name])
            name = " ".join(p for p in [first_name, middle_name, last_name] if p).strip()

            if not name:
                missing_names_count += 1
                row_data_str = ", ".join(f"Col_{i}: {v}" for i, v in enumerate(row) if v)
                missing_name_writer.writerow({
                    "source_file": filename,
                    "row_index": reader.line_num,
                    "raw_row_data": row_data_str
                })

            # 2. Process and cleanly stitch father/husband name components
            father_first  = clean_field_string(row[idx_ff_name])
            father_middle = clean_field_string(row[idx_fm_name])
            father_last   = clean_field_string(row[idx_fl_name])
            father_name   = " ".join(p for p in [father_first, father_middle, father_last] if p).strip()

            # 3. Combine geospatial address fields format: Address, District, State, Country
            addr_parts = [
                " ".join(row[idx_address].strip().replace("\n", " ").split()),
                clean_field_string(row[idx_district]),
                clean_field_string(row[idx_state]),
                clean_field_string(row[idx_country])
            ]
            address = ", ".join(p for p in addr_parts if p)

            # 4. Clean up pin code text structure
            pin_code = clean_field_string(row[idx_pin])

            # 5. Extract dividend dynamically across leaky cells while dropping conflicting dates
            net_dividend = extract_net_dividend(
                row[idx_inv_type],
                row[idx_amount],
                row[idx_proposed]
            )

            # 6. Sanitize Aadhar value inputs under generic compliance rules
            raw_aadhar = clean_field_string(row[idx_aadhar])
            aadhar_no = "[Aadhaar Omitted]" if raw_aadhar and raw_aadhar.isdigit() else raw_aadhar

            writer.writerow({
                "folio_id":         clean_field_string(row[idx_folio]),
                "name":             name,
                "father_name":      father_name,
                "address":          address,
                "pin_code":         pin_code,
                "net_dividend":     net_dividend,
                "date_of_transfer": parse_date(row[idx_proposed]),
                "dp_id":            clean_field_string(row[idx_dpid]),
                "pan_no":           clean_field_string(row[idx_pan]),
                "date_of_birth":    parse_date(row[idx_dob]),
                "aadhar_no":        aadhar_no,
                "joint_holder_name": clean_field_string(row[idx_joint])
            })
            rows_processed += 1

    return rows_processed, missing_names_count


def main():
    parser = argparse.ArgumentParser(description="Map raw shifting tables cleanly to target Shares Database Layout.")
    parser.add_argument("input_dir", help="Path to raw input CSV directory")
    parser.add_argument("-o", "--output-dir", required=True, help="Path to output directory")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"[ERROR] Input directory not found: {args.input_dir}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    log_file_path = os.path.join(args.output_dir, "missing_names_log.csv")

    total_files_processed = 0
    total_missing_names = 0

    with open(log_file_path, "w", newline="", encoding="utf-8") as log_file:
        log_fields = ["source_file", "row_index", "raw_row_data"]
        log_writer = csv.DictWriter(log_file, fieldnames=log_fields, quoting=csv.QUOTE_ALL)
        log_writer.writeheader()

        for file in sorted(os.listdir(args.input_dir)):
            if file.lower().endswith(".csv") and file != "missing_names_log.csv":
                input_file_path = os.path.join(args.input_dir, file)
                base, ext = os.path.splitext(file)
                output_file_path = os.path.join(args.output_dir, f"{base}_transformed{ext}")

                print(f"[PROCESSING] {file}...")
                row_count, missing_count = transform_single_file(input_file_path, output_file_path, log_writer)
                
                suffix = f"  (⚠️ Found {missing_count} rows missing names)" if missing_count else ""
                print(f"             -> Extracted {row_count} rows to updated Model Layout.{suffix}")
                    
                total_files_processed += 1
                total_missing_names += missing_count

    print("-" * 50)
    print(f"[DONE] Transformed {total_files_processed} file(s) into {args.output_dir}")
    if total_missing_names:
        print(f"[WARN] Total missing names: {total_missing_names} — Logged at {log_file_path}")


if __name__ == "__main__":
    main()