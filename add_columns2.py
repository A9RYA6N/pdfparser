import csv
import sys
import os
import io
import argparse

# Exactly matches your target multi-line format structure
TARGET_HEADERS = [
    "Investor First Name", "Investor Middle \nName", "Investor Last \nName", 
    "Father/Husband \nFirst Name", "Father/Husband \nMiddle Name", "Father/Husband Last \nName", 
    "Address", "Country", "State", "District", "Pin Code", "Folio Number", 
    "DP Id-Client Id-\nAccount Number", "Investment Type", "Amount \ntransferred", 
    "Proposed Date of \ntransfer to IEPF\n(DD-MON-YYYY)", "PAN", "Date of Birth", 
    "Aadhar Number", "Nominee Name", "Joint Holder \nName", "Remarks", 
    "Is the \nInvestment \n(amount / \nshares )under \nany litigation.", 
    "Is the shares \ntransfer from \nunpaid suspense \naccount \n(Yes/No)", "Financial Year"
]


def replace_headers(file_path):
    try:
        # 1. Read the existing rows completely
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            all_rows = list(reader)

        if not all_rows:
            print(f"[WARN] {os.path.basename(file_path)} is empty. Skipping.")
            return False

        # 2. Drop the old header row (index 0)
        data_rows = all_rows[2:]

        # 3. Write back the brand new target headers followed by the old body data
        print(f"[REPLACING] Overwriting headers for: {os.path.basename(file_path)}")
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            
            # Write new schema
            writer.writerow(TARGET_HEADERS)
            
            # Write remaining body data lines
            writer.writerows(data_rows)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to modify layout for {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Remove old headers and replace with the required layout structure in CSV files."
    )
    parser.add_argument("directory", help="Path to target directory containing raw CSVs")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"[ERROR] Target directory path not found: {args.directory}")
        sys.exit(1)

    print(f"[START] Commencing header replacement in: {args.directory}\n" + "-" * 50)

    fixed_count = 0
    total_csvs  = 0

    # Crawl target directory tree and replace row index 0 unconditionally
    for root, _, files in os.walk(args.directory):
        for file in files:
            if file.lower().endswith(".csv"):
                total_csvs += 1
                full_path = os.path.join(root, file)
                if replace_headers(full_path):
                    fixed_count += 1

    print("-" * 50)
    print(f"[DONE] Evaluated {total_csvs} CSV paths. Headers successfully replaced in {fixed_count} files.")


if __name__ == "__main__":
    main()