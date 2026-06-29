import os
import sys
import csv
import argparse
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
 
from sqlalchemy.orm import Session
 
from db.models.sharesModel import Shares
from db.config.db import SessionLocal
 
 
# ── Type casting helpers ──────────────────────────────────────────────────────
 
def to_int(value: str | None) -> int | None:
    """Cast to int, return None if blank or unparseable."""
    if not value or not value.strip():
        return None
    try:
        return int(float(value.strip()))   # handles "534211.0" style strings too
    except (ValueError, TypeError):
        print(f"[WARN] Could not cast to int: {repr(value)} — storing NULL")
        return None
 
 
def to_decimal(value: str | None) -> Decimal | None:
    """Cast to Decimal for Numeric(10,2) columns."""
    if not value or not value.strip():
        return None
    try:
        return Decimal(value.strip())
    except (InvalidOperation, TypeError):
        print(f"[WARN] Could not cast to Decimal: {repr(value)} — storing NULL")
        return None
 
 
def to_date(value: str | None) -> date | None:
    """
    Parse YYYY-MM-DD string (output of transform script) into a Python date.
    Falls back to DD-MON-YYYY in case raw untransformed files are passed in.
    """
    if not value or not value.strip():
        return None
    clean = value.strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    print(f"[WARN] Could not parse date: {repr(value)} — storing NULL")
    return None
 
 
def to_str(value: str | None) -> str | None:
    """Return stripped string or None if blank."""
    if not value or not value.strip():
        return None
    return value.strip()
 
 
# ── Row casting ───────────────────────────────────────────────────────────────
 
def cast_row(rec: dict) -> dict:
    """
    Map raw CSV string values to the correct Python types
    matching the Shares SQLAlchemy model columns.
    """
    return {
        "folio_id":         to_str(rec.get("folio_id")),
        "company":          to_str(rec.get("company")),
        "name":             to_str(rec.get("name")),
        "father_name":      to_str(rec.get("father_name")),
        "address":          to_str(rec.get("address")),
        "pin_code":         to_int(rec.get("pin_code")),
        "number_of_shares": to_int(rec.get("number_of_shares")),
        "net_dividend":     to_decimal(rec.get("net_dividend")),
        "war_no":           to_int(rec.get("war_no")),
        "chq_no":           to_int(rec.get("chq_no")),
        "year":             to_int(rec.get("year")),
        "date_of_transfer": to_date(rec.get("date_of_transfer")),
    }
 
 
# ── Core seeder ───────────────────────────────────────────────────────────────
 
def createSharesViaCSV(db: Session, path: str) -> int:
    # Resolve files to process
    if os.path.isdir(path):
        print(f"[*] Scanning directory '{path}' for CSV files...")
        csv_files = sorted(
            os.path.join(path, f)
            for f in os.listdir(path)
            if f.lower().endswith(".csv")
        )
        print(f"[*] Found {len(csv_files)} CSV file(s) to stage.")
    elif os.path.isfile(path):
        csv_files = [path]
    else:
        print(f"[ERROR] Target path invalid: {path}")
        return 0
 
    total_staged = 0
 
    try:
        for csv_file in csv_files:
            print(f"[*] Staging: {os.path.basename(csv_file)}")
 
            with open(csv_file, mode="r", encoding="utf-8") as f:
                raw_records = list(csv.DictReader(f))
 
            db_records = []
            for i, rec in enumerate(raw_records, start=1):
                try:
                    casted = cast_row(rec)
                    db_records.append(Shares(**casted))
                except Exception as e:
                    print(f"[WARN] Row {i} in {os.path.basename(csv_file)} skipped: {e}")
                    continue
 
            db.add_all(db_records)
            total_staged += len(db_records)
            print(f"    → {len(db_records)} rows staged.")
 
        # Single atomic commit across all files
        print(f"\n[*] Committing {total_staged} total records...")
        db.commit()
        print(f"[+] Success — {total_staged} records committed.")
        return total_staged
 
    except Exception as e:
        db.rollback()
        print(f"\n[-] CRITICAL FAILURE: Transaction rolled back. Zero rows saved.")
        print(f"[-] Error: {e}")
        raise
 
 
# ── Entry point ───────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed transformed CSV records into the Shares table."
    )
    parser.add_argument(
        "path",
        help="Path to a single CSV file or a directory of CSV files"
    )
    args = parser.parse_args()
 
    if not os.path.exists(args.path):
        print(f"[ERROR] Path does not exist: {args.path}")
        sys.exit(1)
 
    print("[*] Connecting to database...")
    db_session = SessionLocal()
 
    try:
        createSharesViaCSV(db=db_session, path=args.path)
    except Exception as e:
        print(f"[CRITICAL] Execution stopped: {e}")
        sys.exit(1)
    finally:
        print("[*] Closing database connection.")
        db_session.close()