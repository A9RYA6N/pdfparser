import csv
import sys
import os
import argparse

HEADER_ANCHOR = "NAME OF THE SHARESHOLDERS"


def find_header_idx(rows):
    """Return the index of the row that contains the real header anchor, or -1."""
    for i, row in enumerate(rows):
        if any(HEADER_ANCHOR in cell for cell in row):
            return i
    return -1


def strip_title_rows(file_path):
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    header_idx = find_header_idx(rows)

    if header_idx == -1:
        print(f"[SKIP] {os.path.basename(file_path)} — header anchor not found.")
        return False

    if header_idx == 0:
        print(f"[SKIP] {os.path.basename(file_path)} — already starts with header.")
        return False

    # Rewrite file starting from the real header row
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerows(rows[header_idx:])

    print(f"[FIXED] {os.path.basename(file_path)} — removed {header_idx} title row(s).")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Strip title rows above the real header in CSV files."
    )
    parser.add_argument("path", help="Path to a single CSV file or a directory of CSV files")
    args = parser.parse_args()

    if os.path.isfile(args.path):
        strip_title_rows(args.path)

    elif os.path.isdir(args.path):
        fixed = 0
        total = 0
        for file in sorted(os.listdir(args.path)):
            if file.lower().endswith(".csv"):
                total += 1
                if strip_title_rows(os.path.join(args.path, file)):
                    fixed += 1
        print("-" * 50)
        print(f"[DONE] Checked {total} file(s). Fixed {fixed}.")

    else:
        print(f"[ERROR] Path not found: {args.path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
