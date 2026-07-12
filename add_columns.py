import csv
import sys
import os
import io
import argparse

# Exactly matches your newest target format structure with extended column definitions
TARGET_HEADERS = [
    "Investor First Name", "Investor Middle \nName", "Investor Last \nName", 
    "Father/Husband \nFirst Name", "Father/Husband \nMiddle Name", "Father/Husband Last \nName", 
    "Address", "Country", "State", "District", "Pin Code", "Folio Number", 
    "DP Id-Client Id-\nAccount Number", "Investment Type", "Amount \ntransferred", 
    "Proposed Date of transfer \nto IEPF\n(DD-MON-YYYY)", "PAN", "Date of Birth", 
    "Aadhar Number", "Nominee Name", "Joint Holder \nName", "Remarks", 
    "Is the \nInvestment \n(amount / \nshares )under \nany litigation.", 
    "Is the shares \ntransfer from \nunpaid suspense \naccount \n(Yes/No)", "Financial Year"
]


def normalize_row(row):
    """Normalize fields by stripping and flattening multi-line whitespace variations."""
    return [" ".join(str(cell).strip().split()).upper() for cell in row]


def inject_headers_if_missing(file_path):
    try:
        # 1. Read the very first row to check for existing headers
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            first_row = next(reader, [])

        # Normalize strings for comparison
        first_normalized = normalize_row(first_row)

        # Skip if the file already contains signature unique columns from this specific layout
        if "INVESTOR FIRST NAME" in first_normalized or "FINANCIAL YEAR" in first_normalized:
            print(f"[SKIP] {os.path.basename(file_path)} — Already initialized with schema.")
            return False

        # 2. Read existing content to prepare for header prepending
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            existing_content = f.read()

        # Generate a clean quoted CSV string wrapper for headers
        header_buf = io.StringIO()
        csv.writer(header_buf, quoting=csv.QUOTE_ALL).writerow(TARGET_HEADERS)
        header_line = header_buf.getvalue()

        # 3. Prepend the header row safely
        print(f"[FIXING] Injecting headers into: {os.path.basename(file_path)}")
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(header_line + existing_content)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to modify file layout for {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inject required comprehensive regulatory layout headers into raw IEPF investor files."
    )
    parser.add_argument("directory", help="Path to target directory containing raw CSVs")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"[ERROR] Target directory path not found: {args.directory}")
        sys.exit(1)

    print(f"[START] Scanning target folder: {args.directory}\n" + "-" * 50)

    fixed_count = 0
    total_csvs  = 0

    # Crawl target directory tree 
    for root, _, files in os.walk(args.directory):
        for file in files:
            if file.lower().endswith(".csv"):
                total_csvs += 1
                full_path = os.path.join(root, file)
                if inject_headers_if_missing(full_path):
                    fixed_count += 1

    print("-" * 50)
    print(f"[DONE] Evaluated {total_csvs} CSV paths. Headers injected into {fixed_count} files.")


if __name__ == "__main__":
    main()