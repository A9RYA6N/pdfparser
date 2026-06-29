import os
import sys
import argparse

TARGET_HEADERS = ["FOLIO_ID", "NAME_1", "ADD_1", "ADD_2", "ADD_3", "CITY", "PIN", "NET_DIV", "WAR_NO", "CHQ_NO", "DD_DATE"]
TARGET_HEADER_LINE = ",".join(f'"{h}"' for h in TARGET_HEADERS)


def fix_csv_headers(file_path):
    """Checks if a file has the correct headers. If not, prepends them."""
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            first_line = f.readline().strip()

        # Clean quotes and spaces to check header structure accurately
        clean_first_line = first_line.replace('"', '').replace("'", "").strip()
        clean_target = ",".join(TARGET_HEADERS)

        if clean_first_line == clean_target:
            print(f"[SKIP] {os.path.basename(file_path)} already has correct headers.")
            return False

        # If headers don't match, read entire content and prepend target headers
        print(f"[FIXING] Adding headers to: {os.path.basename(file_path)}")
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(TARGET_HEADER_LINE + "\n" + content)
        return True

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Check and inject headers into all CSV files inside a directory.")
    parser.add_argument("directory", help="Path to the directory containing raw CSV files")
    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        print(f"[ERROR] Directory not found: {args.directory}")
        sys.exit(1)

    print(f"[START] Scanning directory: {args.directory}\n" + "-"*50)
    
    fixed_count = 0
    total_csvs = 0

    for root, _, files in os.walk(args.directory):
        for file in files:
            if file.lower().endswith(".csv"):
                total_csvs += 1
                full_path = os.path.join(root, file)
                if fix_csv_headers(full_path):
                    fixed_count += 1

    print("-"*50)
    print(f"[DONE] Checked {total_csvs} CSV files. Injected headers into {fixed_count} files.")


if __name__ == "__main__":
    main()