import os
import sys
import argparse

import pandas as pd

RENAME_MAP = {
    "folio_no": "folio_id",
    "warrant_no": "war_no",
    "shares": "number_of_shares",
    "amount": "net_dividend",
}


def rename_headers(path):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols_to_rename = {k: v for k, v in RENAME_MAP.items() if k in df.columns}
    if not cols_to_rename:
        return False
    df.rename(columns=cols_to_rename, inplace=True)
    df.to_csv(path, index=False)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Rename CSV headers in-place to match Shares model column names."
    )
    parser.add_argument("target_dir", help="Directory containing CSV files to update")
    args = parser.parse_args()

    if not os.path.isdir(args.target_dir):
        print(f"[ERROR] Directory not found: {args.target_dir}")
        sys.exit(1)

    csv_files = sorted(f for f in os.listdir(args.target_dir) if f.lower().endswith(".csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {args.target_dir}")
        sys.exit(1)

    updated = 0
    for file in csv_files:
        path = os.path.join(args.target_dir, file)
        changed = rename_headers(path)
        status = "updated" if changed else "skipped (no matching columns)"
        print(f"[{'OK' if changed else '--'}] {file} — {status}")
        if changed:
            updated += 1

    print(f"\n[DONE] {updated}/{len(csv_files)} files updated in {args.target_dir}")


if __name__ == "__main__":
    main()
