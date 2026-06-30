import os
import sys
import csv
import io
import argparse

TARGET_HEADERS = [
    "Investor First \nName",
    "Investor Middle \nName",
    "Investor Last \nName",
    "Father/Husband \nFirst Name",
    "Father/Husband \nMiddle Name",
    "Father/Husband Last \nName",
    "Address",
    "Country",
    "State",
    "District",
    "Pin Code",
    "Folio Number",
    "DP Id-Client Id-\nAccount Number",
    "Investment Type",
    "Amount \ntransferred",
    "Date of event \n(date of declaration of \ndividend/redemption date of \npreference shares/date of \nmaturity of \nbonds/debentures/application \nmoney refundable/interest \nthereon\n(DD-MON-YYYY)",
]

# Normalized versions for comparison (collapse newlines + strip)
TARGET_NORMALIZED = [h.replace("\n", " ").strip().lower() for h in TARGET_HEADERS]


def fix_csv_headers(file_path):
    try:
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            first_row = next(reader, [])

        first_row_normalized = [c.replace("\n", " ").strip().lower() for c in first_row]

        if first_row_normalized == TARGET_NORMALIZED:
            print(f"[SKIP] {os.path.basename(file_path)} already has correct headers.")
            return False

        # Read the raw file content to prepend the header row
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            existing_content = f.read()

        # Build a properly quoted CSV header row in memory
        header_buf = io.StringIO()
        csv.writer(header_buf, quoting=csv.QUOTE_ALL).writerow(TARGET_HEADERS)
        header_line = header_buf.getvalue()

        print(f"[FIXING] Adding headers to: {os.path.basename(file_path)}")
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            f.write(header_line + existing_content)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Check and inject headers into all CSV files inside a directory."
    )
    parser.add_argument("directory", help="Path to the directory containing raw CSV files")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"[ERROR] Directory not found: {args.directory}")
        sys.exit(1)

    print(f"[START] Scanning directory: {args.directory}\n" + "-" * 50)

    fixed_count = 0
    total_csvs = 0

    for root, _, files in os.walk(args.directory):
        for file in files:
            if file.lower().endswith(".csv"):
                total_csvs += 1
                full_path = os.path.join(root, file)
                if fix_csv_headers(full_path):
                    fixed_count += 1

    print("-" * 50)
    print(f"[DONE] Checked {total_csvs} CSV files. Injected headers into {fixed_count} files.")


if __name__ == "__main__":
    main()
