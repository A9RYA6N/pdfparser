#!/usr/bin/env python3
"""
PDF Table Extractor
A clean and safe utility to extract tables from PDF files using Camelot.
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
        
    if missing_packages:
        print("[-] Missing Python dependencies:", file=sys.stderr)
        for pkg in missing_packages:
            print(f"    - {pkg}", file=sys.stderr)
        sys.exit(1)

def validate_pdf_path(pdf_path):
    """
    Safely validate the PDF path.
    Checks that the file exists, is indeed a file, and has a .pdf extension.
    """
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

def extract_tables(pdf_path, pages='1', flavor='lattice'):
    """
    Extract tables from the specified PDF using Camelot.
    
    Parameters:
        pdf_path (str): Validated absolute path to the PDF file.
        pages (str): Pages to extract (e.g., '1', '1-3', 'all').
        flavor (str): Camelot flavor ('lattice' or 'stream').
    """
    import camelot
    
    print(f"[*] Extracting tables from: {pdf_path}")
    print(f"[*] Parsing pages: {pages}")
    print(f"[*] Using extraction flavor: {flavor}")
    print("[*] Running Camelot extraction...")
    
    try:
        # read_pdf is camelot's main extraction method
        tables = camelot.read_pdf(pdf_path, pages=pages, flavor=flavor)
        return tables
    except RuntimeError as e:
        err_msg = str(e).lower()
        if 'ghostscript' in err_msg:
            print("\n[!] Error: Ghostscript is not installed or not in system PATH.", file=sys.stderr)
            print("    Camelot requires Ghostscript to extract tables from PDFs.", file=sys.stderr)
            if sys.platform == 'darwin':
                print("    Fix: Run 'brew install ghostscript' in your terminal.", file=sys.stderr)
            elif sys.platform.startswith('linux'):
                print("    Fix: Run 'sudo apt-get install ghostscript' in your terminal.", file=sys.stderr)
            else:
                print("    Fix: Install Ghostscript from: https://www.ghostscript.com/download.html", file=sys.stderr)
        else:
            print(f"\n[!] Camelot Runtime Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Unexpected error occurred during extraction: {e}", file=sys.stderr)
        sys.exit(1)

def display_table_heads(tables):
    """
    Display details and the head (first few rows) of each extracted table.
    """
    num_tables = len(tables)
    print(f"\n[+] Extraction complete. Found {num_tables} table(s).")
    
    if num_tables == 0:
        print("No tables were detected. If the tables do not have clear grid lines, try running with '--flavor stream'.")
        return
        
    # Attempt to import tabulate for nicer grid styling
    has_tabulate = False
    try:
        from tabulate import tabulate
        has_tabulate = True
    except ImportError:
        pass

    for i, table in enumerate(tables):
        print("\n" + "="*80)
        print(f" TABLE {i + 1} (Page {table.page})")
        print(f" Shape: {table.df.shape[0]} rows x {table.df.shape[1]} columns")
        print(f" Accuracy: {table.parsing_report.get('accuracy', 0):.2f}% | Whitespace: {table.parsing_report.get('whitespace', 0):.2f}%")
        print("="*80)
        
        # Display the first 5 rows (head) of the table DataFrame
        df_head = table.df.head(5)
        
        if has_tabulate:
            print(tabulate(df_head, headers='keys', tablefmt='fancy_grid', showindex=False))
        else:
            print(df_head.to_string(index=False))
            
    print("\n" + "="*80)

def main():
    parser = argparse.ArgumentParser(
        description="Extract tables from PDF files using Camelot and display their heads."
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the target PDF file."
    )
    parser.add_argument(
        "-p", "--pages",
        default="1",
        help="Pages to extract tables from. Examples: '1', '1,2,5', '1-3', 'all'. Default is '1'."
    )
    parser.add_argument(
        "-f", "--flavor",
        choices=["lattice", "stream"],
        default="lattice",
        help="Camelot extraction flavor. 'lattice' uses PDF graphical elements (lines), 'stream' uses whitespace margins. Default is 'lattice'."
    )
    parser.add_argument(
        "-o", "--output-dir",
        help="Optional directory path to export extracted tables to CSV format."
    )
    
    args = parser.parse_args()
    
    # 1. Verify dependencies are available
    check_dependencies()
    
    # 2. Validate PDF path
    validated_path = validate_pdf_path(args.pdf_path)
    
    # 3. Extract tables
    tables = extract_tables(validated_path, pages=args.pages, flavor=args.flavor)
    
    # 4. Display heads of extracted tables
    display_table_heads(tables)
    
    # 5. Export if output directory is provided
    if args.output_dir and len(tables) > 0:
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"[*] Exporting tables to: {args.output_dir}")
        for i, table in enumerate(tables):
            csv_path = os.path.join(args.output_dir, f"table_page_{table.page}_idx_{i+1}.csv")
            table.to_csv(csv_path)
            print(f"    - Saved table {i+1} to {csv_path}")
        print("[+] Export finished.")

if __name__ == "__main__":
    main()
