import csv
import sys
import os
import argparse

def process_file(file_path, year_value):
    """Appends a year column to the end of a CSV file."""
    try:
        # 1. Read existing data rows and column headers
        with open(file_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            original_fields = reader.fieldnames or []
            rows = list(reader)

        if not original_fields:
            print(f"[SKIP] Empty or invalid file: {os.path.basename(file_path)}")
            return False

        # 2. Add the new field to the end of the header array (if not already present)
        if "year" in original_fields:
            new_fields = original_fields
        else:
            new_fields = original_fields + ["year"]

        # 3. Write data back to the same file path safely
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=new_fields, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            for row in rows:
                row["year"] = year_value  # Set the year integer string
                writer.writerow(row)
                
        print(f"[SUCCESS] Appended year {year_value} to: {os.path.basename(file_path)}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Append a 'year' integer column at the end of transformed CSV files."
    )
    parser.add_argument("path", help="Path to a single CSV file or an entire directory folder")
    parser.add_argument("-y", "--year", required=True, type=int, help="The 4-digit year to append (e.g., 2016)")
    args = parser.parse_args()

    # Determine processing mode based on filesystem metadata
    if os.path.isdir(args.path):
        print(f"[*] Scanning directory workspace '{args.path}'...")
        csv_files = [os.path.join(args.path, f) for f in os.listdir(args.path) if f.lower().endswith('.csv')]
        print(f"[*] Found {len(csv_files)} CSV file(s) to modify.\n" + "-"*50)
        
        updated_count = 0
        for csv_file in csv_files:
            if process_file(csv_file, args.year):
                updated_count += 1
        print("-"*50 + f"\n[DONE] Successfully appended year '{args.year}' to {updated_count} file(s).")
        
    elif os.path.isfile(args.path):
        print(f"[*] Target recognized as a single file: {args.path}\n" + "-"*50)
        process_file(args.path, args.year)
        print("-"*50 + "\n[DONE]")
    else:
        print(f"[ERROR] Specified file path context invalid: {args.path}")
        sys.exit(1)


if __name__ == "__main__":
    main()