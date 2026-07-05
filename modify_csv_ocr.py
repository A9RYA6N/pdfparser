import os
import re
import sys
import argparse

import pandas as pd

COLUMNS = ["folio_id", "war_no", "name", "number_of_shares", "net_dividend", "micr_no"]


# ── Cell cleaners ────────────────────────────────────────────────────────────

def clean_amount(value):
    """Fix OCR garbage in amount cells: stray chars, comma-as-decimal, thousands separators."""
    s = "" if value is None else str(value).strip()
    if not s:
        return ""

    s = re.sub(r"[^\d.,]", "", s)  # strip stray letters/underscores etc (e.g. "900_")

    if re.match(r"^\d+,\d{2}$", s):                  # "360,00" -> misread decimal point
        s = s.replace(",", ".")
    elif re.match(r"^\d{1,3}(,\d{3})+(\.\d+)?$", s):  # "1,425.00" -> thousands separator
        s = s.replace(",", "")

    if s and "." not in s:
        s += ".00"

    return s


def clean_folio_id(value):
    """Remove phantom number+newline prefix from folio IDs caused by img2table merging
    the SR NO cell with the adjacent folio cell, e.g. '4\\nIN3011351019048' -> 'IN3011351019048'."""
    s = "" if value is None else str(value).strip()
    if not s:
        return ""
    s = re.sub(r"^\d+\n", "", s)
    return s.strip()


def clean_int_cell(value):
    """Strip OCR garbage from an integer-like cell (SR NO, Warrant No, MICR No, Shares)."""
    s = "" if value is None else str(value).strip()
    if not s:
        return ""
    s = re.sub(r"\.0+$", "", s)   # drop float artifact, e.g. "50.0" -> "50"
    s = re.sub(r"[^\d]", "", s)   # strip any remaining non-digit junk
    return s


# ── Structural fixes ─────────────────────────────────────────────────────────

def merge_split_name_rows(df):
    """
    Handles rows where a long name wrapped onto its own line in the PDF and
    was extracted as a separate row with all data columns empty.
    Appends the name fragment to the previous data row and deletes the stub row.
    Handles consecutive continuation rows by always targeting the last real row.
    """
    data_cols = ["folio_id", "war_no", "number_of_shares", "net_dividend", "micr_no"]
    to_drop = []
    last_data_iloc = None

    for i in range(len(df)):
        row = df.iloc[i]
        is_continuation = (
            all(str(row[c]).strip() == "" for c in data_cols)
            and str(row["name"]).strip() != ""
        )
        if is_continuation and last_data_iloc is not None:
            prev_name = str(df.iloc[last_data_iloc]["name"]).strip()
            extra = str(row["name"]).strip()
            df.at[df.index[last_data_iloc], "name"] = f"{prev_name} {extra}"
            to_drop.append(df.index[i])
        else:
            last_data_iloc = i

    return df.drop(index=to_drop).reset_index(drop=True)


def detect_rate(df):
    """Detect per-share rate from a file's own known rows (mode of net_dividend / shares)."""
    s_shares = pd.to_numeric(df["number_of_shares"], errors="coerce")
    s_amount = pd.to_numeric(df["net_dividend"], errors="coerce")
    known = s_shares.notna() & s_amount.notna() & (s_shares > 0) & (s_amount > 0)
    if known.sum() == 0:
        return None
    rates = (s_amount[known] / s_shares[known]).round(4)
    return rates.mode().iloc[0]


def infer_missing_shares(df):
    """Fill missing share counts using the rate detected from this file's own known rows."""
    rate = detect_rate(df)
    if rate is None:
        return df

    s_shares = pd.to_numeric(df["number_of_shares"], errors="coerce")
    s_amount = pd.to_numeric(df["net_dividend"], errors="coerce")

    missing = df.index[s_shares.isna() & s_amount.notna() & (s_amount > 0)]
    for idx in missing:
        inferred = s_amount[idx] / rate
        if inferred > 0 and abs(inferred - round(inferred)) < 0.01:
            s_shares[idx] = int(round(inferred))

    df = df.copy()
    df["number_of_shares"] = s_shares
    return df


# ── File-level transform ─────────────────────────────────────────────────────

def load_csv(path):
    df = pd.read_csv(path, header=0, dtype=str, keep_default_na=False)
    if df.shape[1] != len(COLUMNS) + 1:
        print(f"[ERROR] Skipping {os.path.basename(path)}: expected {len(COLUMNS) + 1} columns, found {df.shape[1]}")
        return None
    df = df.drop(columns=df.columns[0])  # drop SR NO
    df.columns = COLUMNS
    return df


def transform_single_file(df):
    df = df.copy()
    df["folio_id"] = df["folio_id"].map(clean_folio_id)
    df["net_dividend"] = df["net_dividend"].map(clean_amount)
    df["war_no"] = df["war_no"].map(clean_int_cell)
    df["micr_no"] = df["micr_no"].map(clean_int_cell)
    df["number_of_shares"] = df["number_of_shares"].map(clean_int_cell)

    df = merge_split_name_rows(df)
    df = infer_missing_shares(df)
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Clean OCR artifacts and recalculate missing share counts "
                     "in dividend CSVs extracted by extract_tables_ocr.py."
    )
    parser.add_argument("input_dir", help="Directory containing raw OCR-extracted CSV files")
    parser.add_argument("-o", "--output-dir", required=True, help="Directory to write cleaned CSVs")
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        print(f"[ERROR] Input directory not found: {args.input_dir}")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    csv_files = sorted(f for f in os.listdir(args.input_dir) if f.lower().endswith(".csv"))
    if not csv_files:
        print(f"[ERROR] No CSV files found in {args.input_dir}")
        sys.exit(1)

    print(f"[INFO] Reading from : {args.input_dir}")
    print(f"[INFO] Outputting to: {args.output_dir}\n" + "-" * 50)

    total_rows = 0
    total_files = 0
    for file in csv_files:
        df = load_csv(os.path.join(args.input_dir, file))
        if df is None:
            continue
        cleaned = transform_single_file(df)
        rate = detect_rate(cleaned)
        rate_str = f"rate={rate}" if rate is not None else "rate=unknown"
        base, ext = os.path.splitext(file)
        output_path = os.path.join(args.output_dir, f"{base}_cleaned{ext}")
        cleaned.to_csv(output_path, index=False)
        print(f"[PROCESSING] {file} -> {len(cleaned)} rows ({rate_str})")
        total_rows += len(cleaned)
        total_files += 1

    print("-" * 50)
    print(f"[DONE] Cleaned {total_files} files, {total_rows} rows total -> {args.output_dir}")


if __name__ == "__main__":
    main()
