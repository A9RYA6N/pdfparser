import csv
import sys
import os
import argparse

def process_file(file_path, company_name):
    """Inserts a company column right before the 'name' column in a CSV."""
    try:
        # 1. Read existing data
        with open(file_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            original_fields = reader.fieldnames or []
            rows = list(reader)

        if not original_fields:
            print(f"[SKIP] Empty or invalid file: {os.path.basename(file_path)}")
            return False

        if "company" in original_fields:
            print(f"[SKIP] 'company' column already exists in: {os.path.basename(file_path)}")
            return False

        if "name" not in original_fields:
            print(f"[ERROR] Could not find 'name' column to reference positioning in: {os.path.basename(file_path)}")
            return False

        # 2. Re-map headers to place 'company' right before 'name'
        name_idx = original_fields.index("name")
        new_fields = original_fields[:name_idx] + ["company"] + original_fields[name_idx:]

        # 3. Write back the updated content to the same file
        with open(file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=new_fields, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            for row in rows:
                row["company"] = company_name  # Inject user-defined company name
                writer.writerow(row)
                
        print(f"[SUCCESS] Updated: {os.path.basename(file_path)}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inject a 'company' column right before the 'name' column in transformed CSV files."
    )
    parser.add_argument("path", help="Path to a single CSV file or an entire directory")
    parser.add_argument("-c", "--company", required=True, help="The company name to populate across the rows")
    args = parser.parse_args()

    # Determine if path is a directory or file
    if os.path.isdir(args.path):
        print(f"[*] Scanning folder '{args.path}'...")
        csv_files = [os.path.join(args.path, f) for f in os.listdir(args.path) if f.lower().endswith('.csv')]
        print(f"[*] Found {len(csv_files)} CSV file(s) to process.\n" + "-"*50)
        
        updated_count = 0
        for csv_file in csv_files:
            if process_file(csv_file, args.company):
                updated_count += 1
        print("-"*5+ f"\n[DONE] Successfully injected '{args.company}' into {updated_count} file(s).")
        
    elif os.path.isfile(args.path):
        print(f"[*] Processing single file: {args.path}\n" + "-"*50)
        process_file(args.path, args.company)
        print("-"*5+ "\n[DONE]")
    else:
        print(f"[ERROR] Path not found: {args.path}")
        sys.exit(1)


if __name__ == "__main__":
    main()