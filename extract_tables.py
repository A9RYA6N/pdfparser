#!/usr/bin/env python3
"""
PDF Table Extractor
A versatile utility to extract tables from PDF files natively in batch or sequentially.
"""

import os
import sys
import argparse

def check_dependencies():
    """Verify that required Python packages are installed."""
    missing_packages = []
    
    try:
        import camelot
    except ImportError:
        missing_packages.append("camelot-py (install using `pip install camelot-py[cv]`)")
        
    try:
        import pandas
    except ImportError:
        missing_packages.append("pandas (install using `pip install pandas`)")
        
    try:
        import pypdf
    except ImportError:
        missing_packages.append("pypdf (install using `pip install pypdf`)")
        
    if missing_packages:
        print("[-] Missing Python dependencies:", file=sys.stderr)
        for pkg in missing_packages:
            print(f"    - {pkg}", file=sys.stderr)
        sys.exit(1)

def validate_pdf_path(pdf_path):
    """Safely validate the PDF path."""
    if not pdf_path:
        print("Error: No PDF file path provided.", file=sys.stderr)
        sys.exit(1)
        
    normalized_path = os.path.abspath(pdf_path)
    if not os.path.exists(normalized_path):
        print(f"Error: The file path '{pdf_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(normalized_path):
        print(f"Error: The path '{pdf_path}' is a directory, not a file.", file=sys.stderr)
        sys.exit(1)
    if not pdf_path.lower().endswith('.pdf'):
        print(f"Error: The file '{pdf_path}' does not appear to be a PDF file.", file=sys.stderr)
        sys.exit(1)
        
    return normalized_path

def parse_page_range(pages_str, pdf_path):
    """Expands page layouts into a list of explicit integer values."""
    from pypdf import PdfReader
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
    except Exception:
        total_pages = 9999

    if pages_str.lower() == 'all':
        return list(range(1, total_pages + 1))
        
    pages = set()
    for part in pages_str.split(','):
        if '-' in part:
            start, end = part.split('-')
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
            
    return sorted(list(pages))

def extract_tables_batch(pdf_path, pages_str, flavor):
    """Runs extraction on all target pages simultaneously for maximum speed."""
    import camelot
    try:
        return camelot.read_pdf(pdf_path, pages=pages_str, flavor=flavor)
    except Exception as e:
        handle_runtime_error(e, "Batch Processing")

def extract_tables_single_page(pdf_path, page_num, flavor):
    """Runs extraction on an isolated page to avoid memory overhead or to debug."""
    import camelot
    try:
        return camelot.read_pdf(pdf_path, pages=str(page_num), flavor=flavor)
    except Exception as e:
        handle_runtime_error(e, f"Page {page_num}")

def handle_runtime_error(e, context_msg):
    """Handles dependencies failures like Ghostscript mapping systematically."""
    err_msg = str(e).lower()
    if 'ghostscript' in err_msg:
        print(f"\n[!] Error: Ghostscript is not installed or missing from PATH during {context_msg}.", file=sys.stderr)
        if sys.platform == 'darwin':
            print("    Fix: Run 'brew install ghostscript' in your terminal.", file=sys.stderr)
        elif sys.platform.startswith('linux'):
            print("    Fix: Run 'sudo apt-get install ghostscript' in your terminal.", file=sys.stderr)
        else:
            print("    Fix: Install Ghostscript from: https://www.ghostscript.com/download.html", file=sys.stderr)
    else:
        print(f"\n[!] Camelot Runtime Error [{context_msg}]: {e}", file=sys.stderr)
    sys.exit(1)

def display_single_table(table, global_idx):
    """Renders table metrics and rows head cleanly to console."""
    has_tabulate = False
    try:
        from tabulate import tabulate
        has_tabulate = True
    except ImportError:
        pass

    print("\n" + "="*80)
    print(f" TABLE {global_idx} (Page {table.page})")
    print(f" Shape: {table.df.shape[0]} rows x {table.df.shape[1]} columns")
    print(f" Accuracy: {table.parsing_report.get('accuracy', 0):.2f}% | Whitespace: {table.parsing_report.get('whitespace', 0):.2f}%")
    print("="*80)
    
    df_head = table.df.head(5)
    if has_tabulate:
        print(tabulate(df_head, headers='keys', tablefmt='fancy_grid', showindex=False))
    else:
        print(df_head.to_string(index=False))

def main():
    parser = argparse.ArgumentParser(description="Extract tables from PDF files with custom layout processing modes.")
    parser.add_argument("pdf_path", help="Path to the target PDF file.")
    parser.add_argument("-p", "--pages", default="1", 
                        help="Pages to extract tables from. Examples: '1', '1-3', 'all'. Default is '1'.")
    parser.add_argument("-f", "--flavor", choices=["lattice", "stream"], default="lattice",
                        help="Camelot extraction flavor. 'lattice' uses vector lines, 'stream' uses whitespace.")
    parser.add_argument("-m", "--mode", choices=["batch", "sequential"], default="batch",
                        help="Execution mode. 'batch' is fast (all at once), 'sequential' is page-by-page. Default is 'batch'.")
    parser.add_argument("-o", "--output-dir", help="Optional directory path to export extracted tables to CSV format.")
    
    args = parser.parse_args()
    check_dependencies()
    validated_path = validate_pdf_path(args.pdf_path)
    
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)

    print(f"[*] Starting extraction for: {validated_path}")
    print(f"[*] Flavor: {args.flavor} | Mode: {args.mode}")
    print("-" * 80)

    global_table_counter = 0

    # MODE 1: NATIVE BATCH EXTRACTION (Fastest Approach)
    if args.mode == "batch":
        print("[*] Running native batch compilation...")
        tables = extract_tables_batch(validated_path, args.pages, flavor=args.flavor)
        print(f"[+] Complete. Found {len(tables)} table(s) total.")
        
        for table in tables:
            global_table_counter += 1
            display_single_table(table, global_table_counter)
            if args.output_dir:
                csv_path = os.path.join(args.output_dir, f"table_page_{table.page}_idx_{global_table_counter}.csv")
                table.to_csv(csv_path)
                print(f"    [SAVED] Table saved to {csv_path}")

    # MODE 2: SEQUENTIAL LOOP EXTRACTION (Debugging / Page Progress)
    else:
        page_list = parse_page_range(args.pages, validated_path)
        for current_page in page_list:
            print(f"\n--> Processing Page {current_page}...")
            tables = extract_tables_single_page(validated_path, current_page, flavor=args.flavor)
            print(f"[+] Page {current_page} complete: Found {len(tables)} table(s).")
            
            for i, table in enumerate(tables):
                global_table_counter += 1
                display_single_table(table, global_table_counter)
                if args.output_dir:
                    csv_path = os.path.join(args.output_dir, f"table_page_{table.page}_idx_{i+1}.csv")
                    table.to_csv(csv_path)
                    print(f"    [SAVED] Table saved to {csv_path}")

    print("\n" + "="*80)
    print(f"[FINISHED] All jobs complete. Total tables extracted: {global_table_counter}")
    print("="*80)

if __name__ == "__main__":
    main()