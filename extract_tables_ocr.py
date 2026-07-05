import os
import re
import sys
import argparse


def parse_pages(pages_str):
    """Parse '1', '1-3', '1,2,5', or 'all' into a 0-indexed list (or None for all)."""
    if pages_str.lower() == 'all':
        return None

    pages = set()
    for part in pages_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = part.split('-', 1)
            pages.update(range(int(start) - 1, int(end)))
        else:
            pages.add(int(part) - 1)

    return sorted(pages)


def clean_cell(value):
    """Fix common OCR artifacts in a cell string."""
    if not isinstance(value, str):
        return value
    # Fix decimal comma: "360,00" or "1,440.00" where comma is a misread period
    value = re.sub(r'^(\d+),(\d{2})$', r'\1.\2', value.strip())
    return value


def reconstruct_sr_no(df):
    """
    Reconstruct col 0 (SR NO) which is always a sequential integer.
    img2table drops single-digit numbers (1-9) because their bounding boxes
    are too small to land inside the detected cell region — this fixes that.
    Backfills rows before the first known value, then fills any mid-table gaps.
    """
    import pandas as pd

    col = df.columns[0]
    s = pd.to_numeric(df[col], errors="coerce")

    # Backfill: count down from the first known value
    first_valid_pos = s.first_valid_index()
    if first_valid_pos is not None:
        pos = df.index.get_loc(first_valid_pos)
        val = int(s[first_valid_pos])
        for i in range(pos - 1, -1, -1):
            val -= 1
            s.iloc[i] = val

    # Forward fill any remaining gaps using previous + 1
    for i in range(1, len(s)):
        if pd.isna(s.iloc[i]) and pd.notna(s.iloc[i - 1]):
            s.iloc[i] = s.iloc[i - 1] + 1

    result = df.copy()
    result[col] = s.astype("Int64")
    return result


def infer_missing_shares(df):
    """
    Dividend docs follow: Amount = Shares × per-share rate.
    Auto-detects the rate from rows where both values are known, then fills
    missing share counts where Amount / rate is a whole number.
    Only runs on 7-column dividend tables (col 4 = shares, col 5 = amount).
    """
    import pandas as pd

    if df.shape[1] < 6:
        return df

    shares_col = df.columns[4]
    amount_col = df.columns[5]

    s_shares = pd.to_numeric(df[shares_col], errors="coerce")
    s_amount = pd.to_numeric(df[amount_col], errors="coerce")

    known = s_shares.notna() & s_amount.notna() & (s_shares > 0) & (s_amount > 0)
    if known.sum() == 0:
        return df

    rate = (s_amount[known] / s_shares[known]).round(4).mode().iloc[0]

    missing = df.index[s_shares.isna() & s_amount.notna() & (s_amount > 0)]
    for idx in missing:
        inferred = s_amount[idx] / rate
        if inferred > 0 and abs(inferred - round(inferred)) < 0.01:
            s_shares[idx] = int(round(inferred))

    result = df.copy()
    result[shares_col] = s_shares
    return result


def postprocess_df(df):
    """Apply cell-level OCR cleanup, SR NO reconstruction, and share inference."""
    df = df.apply(lambda col: col.map(clean_cell) if col.dtype == object else col)
    df = reconstruct_sr_no(df)
    df = infer_missing_shares(df)
    return df


def extract_tables_ocr(pdf_path, pages_str='all', borderless=True, min_confidence=20):
    from img2table.document import PDF
    from img2table.ocr import EasyOCR
    import pypdfium2
    from tqdm import tqdm

    print("[*] Loading EasyOCR model (first run downloads ~500MB)...")
    ocr = EasyOCR(lang=["en"])

    doc = pypdfium2.PdfDocument(pdf_path)
    total_pages = len(doc)
    doc.close()

    page_list = parse_pages(pages_str)
    if page_list is None:
        page_list = list(range(total_pages))

    print(f"[*] Extracting tables from: {pdf_path}")
    print(f"[*] Pages: {pages_str} ({len(page_list)} of {total_pages} total)")
    print(f"[*] Borderless: {'on' if borderless else 'off'} | Min confidence: {min_confidence}")

    tables_by_page = {}
    with tqdm(page_list, unit="page", desc="Extracting") as bar:
        for page_idx in bar:
            bar.set_description(f"Page {page_idx + 1}/{total_pages}")
            page_pdf = PDF(
                pdf_path,
                pages=[page_idx],
                detect_rotation=False,
                pdf_text_extraction=True,
            )
            result = page_pdf.extract_tables(
                ocr=ocr,
                implicit_rows=True,
                borderless_tables=borderless,
                min_confidence=min_confidence,
            )
            # result may key by local or absolute index; always store by actual page_idx
            if result:
                tables_by_page[page_idx] = list(result.values())[0]

    return tables_by_page


def display_and_export(tables_by_page, output_dir=None):
    try:
        from tabulate import tabulate
        has_tabulate = True
    except ImportError:
        has_tabulate = False

    total = sum(len(tables) for tables in tables_by_page.values())
    print(f"\n[+] Found {total} table(s) across {len(tables_by_page)} page(s).")

    if total == 0:
        print("No tables detected.")
        print("Tips:")
        print("  - If tables have clear grid lines, try --no-borderless")
        print("  - Check that the PDF pages are not blank or rotated")
        return

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    for page_idx, tables in sorted(tables_by_page.items()):
        for i, table in enumerate(tables):
            print("\n" + "=" * 80)
            print(f" TABLE {i + 1}  —  Page {page_idx + 1}")
            print(f" Shape: {table.df.shape[0]} rows x {table.df.shape[1]} columns")
            print("=" * 80)

            df_head = table.df.head(5)
            if has_tabulate:
                print(tabulate(df_head, headers="keys", tablefmt="fancy_grid", showindex=False))
            else:
                print(df_head.to_string(index=False))

            if output_dir:
                csv_path = os.path.join(output_dir, f"table_page_{page_idx + 1}_idx_{i + 1}.csv")
                postprocess_df(table.df).to_csv(csv_path, index=False)
                print(f"    Saved: {csv_path}")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Extract tables from image-based (scanned) PDFs using OCR."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file.")
    parser.add_argument(
        "-p", "--pages",
        default="all",
        help="Pages to extract. Examples: '1', '1-3', '1,2,5', 'all'. Default: all.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Directory to save extracted tables as CSV files.",
    )
    parser.add_argument(
        "--no-borderless",
        action="store_true",
        help="Disable borderless table detection (use when tables have clear grid lines).",
    )
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=20,
        help="Minimum OCR confidence (0-99). Lower = more cells kept but noisier. Default: 20.",
    )

    args = parser.parse_args()

    pdf_path = os.path.abspath(args.pdf_path)
    if not os.path.isfile(pdf_path) or not pdf_path.lower().endswith(".pdf"):
        print(f"Error: '{args.pdf_path}' is not a valid PDF file.", file=sys.stderr)
        sys.exit(1)

    tables_by_page = extract_tables_ocr(
        pdf_path,
        pages_str=args.pages,
        borderless=not args.no_borderless,
        min_confidence=args.min_confidence,
    )

    display_and_export(tables_by_page, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
