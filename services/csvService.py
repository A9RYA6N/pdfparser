import pandas as pd
import re

def normalize_column_name(col_name: str) -> str:
    """Normalize column names to lowercase alphanumeric only (no spaces, underscores, dots, hyphens)."""
    return "".join(c for c in str(col_name).lower() if c.isalnum())

def has_headers(columns):
    """Check if the columns list contains exact matches of known header names."""
    known_headers = {
        'srno', 'srl', 'slno', 'foliono', 'folioid', 'folionumber', 'folio',
        'name', 'investername', 'investorname', 'nameof1stsoleshareholder', 'nameofshareholder', 'name1',
        'address1', 'address2', 'address3', 'address4', 'add1', 'add2', 'add3', 'add4',
        'address', 'addr', 'city', 'pincode', 'pin', 'postalcode', 'zipcode', 'zip',
        'numberofshares', 'noofshares', 'shares', 'sharescount', 'noofsharesheld',
        'netdividend', 'netdiv', 'amountdueinrs', 'amountdue', 'unpaiddiv', 'unpaiddividend',
        'warno', 'warrantno', 'warrantnumber', 'chqno', 'chequeno', 'chequenumber', 'dddate'
    }
    match_count = 0
    for col in columns:
        col_str = str(col).strip()
        if col_str.startswith('Unnamed:'):
            continue
        norm = normalize_column_name(col_str)
        if norm in known_headers:
            match_count += 1
    return match_count >= 2

def merge_names(df: pd.DataFrame) -> pd.Series:
    """
    Intelligently merge split name columns (e.g. First Name, Middle Name, Last Name)
    into a single series. If a single 'name' column exists, use it.
    """
    cols = df.columns
    normalized_cols = {}
    for c in cols:
        if not str(c).startswith('Unnamed:'):
            normalized_cols[normalize_column_name(c)] = c
    
    # 1. Check if there's already a single "name" column (excluding "first name", etc.)
    name_candidates = ['name', 'investername', 'investorname', 'nameof1stsoleshareholder', 'nameofshareholder', 'name1']
    for cand in name_candidates:
        if cand in normalized_cols:
            return df[normalized_cols[cand]].astype(str).str.strip()
            
    # 2. Check if we have first name, middle name, last name columns
    first_name_col = normalized_cols.get('firstname') or normalized_cols.get('first')
    middle_name_col = normalized_cols.get('middlename') or normalized_cols.get('middle')
    last_name_col = normalized_cols.get('lastname') or normalized_cols.get('last')
            
    if first_name_col:
        def merge_parts(row):
            row_parts = []
            for part_col in [first_name_col, middle_name_col, last_name_col]:
                if part_col and part_col in row and pd.notna(row[part_col]):
                    val = str(row[part_col]).strip()
                    if val and val.lower() not in ['nan', 'none', '']:
                        row_parts.append(val)
            return " ".join(row_parts)
            
        return df.apply(merge_parts, axis=1)
        
    # 3. Fallback: If no name column is found, search for any column containing 'name'
    for c in cols:
        if str(c).startswith('Unnamed:'):
            continue
        norm = normalize_column_name(c)
        if 'name' in norm:
            return df[c].astype(str).str.strip()
            
    return pd.Series([""] * len(df))

def merge_addresses(df: pd.DataFrame) -> pd.Series:
    """
    Intelligently merge multiple address parts (e.g. Address1 to Address4 or Add1 to Add4)
    and the optional CITY column into a single address series.
    """
    cols = df.columns
    normalized_cols = {}
    for c in cols:
        if not str(c).startswith('Unnamed:'):
            normalized_cols[normalize_column_name(c)] = c
            
    has_city = 'city' in normalized_cols
    city_col = normalized_cols['city'] if has_city else None
    
    # Search for numbered parts
    address_patterns = [
        re.compile(r'^(address|add|addr|adr)\d+$', re.IGNORECASE),
        re.compile(r'^(address|add|addr|adr)_\d+$', re.IGNORECASE)
    ]
    
    numbered_cols = []
    for c in cols:
        if str(c).startswith('Unnamed:'):
            continue
        norm = normalize_column_name(c)
        for pattern in address_patterns:
            if pattern.match(c) or pattern.match(norm):
                numbered_cols.append(c)
                break
                
    if numbered_cols:
        # Sort numbered cols by their number suffix
        def get_col_number(name):
            match = re.search(r'\d+', name)
            return int(match.group()) if match else 0
            
        numbered_cols.sort(key=get_col_number)
        
        def merge_row(row):
            parts = []
            for col in numbered_cols:
                val = row[col]
                if pd.notna(val):
                    val_str = str(val).strip().strip(',').strip()
                    if val_str and val_str.lower() not in ['nan', 'none', '']:
                        parts.append(val_str)
            if city_col and pd.notna(row[city_col]):
                city_str = str(row[city_col]).strip().strip(',').strip()
                if city_str and city_str.lower() not in ['nan', 'none', '']:
                    parts.append(city_str)
            return ", ".join(parts)
            
        return df.apply(merge_row, axis=1)
        
    # If no numbered address columns, look for a single address column
    for cand in ['address', 'addr', 'location']:
        if cand in normalized_cols:
            addr_col = normalized_cols[cand]
            if city_col:
                def merge_single_with_city(row):
                    parts = []
                    addr_val = row[addr_col]
                    if pd.notna(addr_val):
                        addr_str = str(addr_val).strip().strip(',').strip()
                        if addr_str and addr_str.lower() not in ['nan', 'none', '']:
                            parts.append(addr_str)
                    city_val = row[city_col]
                    if pd.notna(city_val):
                        city_str = str(city_val).strip().strip(',').strip()
                        if city_str and city_str.lower() not in ['nan', 'none', '']:
                            parts.append(city_str)
                    return ", ".join(parts)
                return df.apply(merge_single_with_city, axis=1)
            else:
                return df[addr_col].astype(str).str.strip().str.strip(',').str.strip()
            
    # Fallback: Find any column containing 'address' or 'addr'
    for c in cols:
        if str(c).startswith('Unnamed:'):
            continue
        norm = normalize_column_name(c)
        if 'address' in norm or 'addr' in norm:
            if city_col:
                def merge_fallback_with_city(row):
                    parts = []
                    addr_val = row[c]
                    if pd.notna(addr_val):
                        addr_str = str(addr_val).strip().strip(',').strip()
                        if addr_str and addr_str.lower() not in ['nan', 'none', '']:
                            parts.append(addr_str)
                    city_val = row[city_col]
                    if pd.notna(city_val):
                        city_str = str(city_val).strip().strip(',').strip()
                        if city_str and city_str.lower() not in ['nan', 'none', '']:
                            parts.append(city_str)
                    return ", ".join(parts)
                return df.apply(merge_fallback_with_city, axis=1)
            else:
                return df[c].astype(str).str.strip().str.strip(',').str.strip()
            
    if city_col:
        return df[city_col].astype(str).str.strip().str.strip(',').str.strip()

    return pd.Series([""] * len(df))

def parse_and_standardize_csv(csv_file_path: str) -> list[dict]:
    """
    Reads any CSV file, normalizes column names, merges names and addresses,
    cleans numeric values, and returns a list of dictionaries ready for DB insert.
    Supports reading files that have missing headers on middle pages.
    """
    # 1. Read first row to determine if headers exist
    temp_df = pd.read_csv(csv_file_path, nrows=1)
    if temp_df.empty:
        return []
    columns_exist = has_headers(temp_df.columns)

    # 2. Read with or without header
    if columns_exist:
        df = pd.read_csv(csv_file_path)
    else:
        df = pd.read_csv(csv_file_path, header=None)
        cols_count = df.shape[1]
        if cols_count == 11:
            df.columns = ['folio_id', 'name', 'Address1', 'Address2', 'Address3', 'CITY', 'pin_code', 'net_dividend', 'war_no', 'chq_no', 'dd_date']
        elif cols_count == 9:
            df.columns = ['sr_no', 'folio_id', 'name', 'Address1', 'Address2', 'Address3', 'Address4', 'pin_code', 'number_of_shares']
        else:
            df.columns = [f"col_{i}" for i in range(cols_count)]
            
    cols = df.columns
    normalized_to_original = {}
    for c in cols:
        if not str(c).startswith('Unnamed:'):
            normalized_to_original[normalize_column_name(c)] = c
    
    # 1. Merge names and addresses
    names = merge_names(df)
    addresses = merge_addresses(df)
    
    # 2. Map other columns using fuzzy match
    folio_id_col = None
    for cand in ['folioid', 'foliono', 'folionumber', 'folionodpclid', 'folionumberofsecurities', 'folio']:
        if cand in normalized_to_original:
            folio_id_col = normalized_to_original[cand]
            break
    if not folio_id_col:
        for c in cols:
            if str(c).startswith('Unnamed:'):
                continue
            if 'folio' in normalize_column_name(c):
                folio_id_col = c
                break
                
    pin_code_col = next((normalized_to_original[k] for k in ['pincode', 'pin', 'postalcode', 'zipcode', 'zip'] if k in normalized_to_original), None)
    shares_col = next((normalized_to_original[k] for k in ['numberofshares', 'noofshares', 'shares', 'sharescount', 'noofsharesheld'] if k in normalized_to_original), None)
    if not shares_col:
        for c in cols:
            if str(c).startswith('Unnamed:'):
                continue
            if 'shares' in normalize_column_name(c):
                shares_col = c
                break
                
    dividend_col = next((normalized_to_original[k] for k in ['netdividend', 'netdiv', 'amountdueinrs', 'amountdue', 'unpaiddiv', 'unpaiddividend'] if k in normalized_to_original), None)
    war_no_col = next((normalized_to_original[k] for k in ['warno', 'warrantno', 'warrantnumber'] if k in normalized_to_original), None)
    chq_no_col = next((normalized_to_original[k] for k in ['chqno', 'chequeno', 'chequenumber'] if k in normalized_to_original), None)

    # Helper parsing functions
    def to_int(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        if not s:
            return None
        try:
            return int(float(s))
        except ValueError:
            return None
            
    def to_float(val):
        if pd.isna(val):
            return None
        s = str(val).strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    # Construct records
    records = []
    for idx, row in df.iterrows():
        # Handle splitting of Sr. No. from FolioNo (just in case raw CSV wasn't cleaned)
        raw_folio = ""
        if folio_id_col and pd.notna(row[folio_id_col]):
            raw_folio = str(row[folio_id_col]).strip()
            parts = raw_folio.split(None, 1)
            if len(parts) > 1 and parts[0].isdigit():
                raw_folio = parts[1].strip()

        # Handle splitting of war_no and chq_no if one is empty and the other has combined values
        raw_war = row[war_no_col] if war_no_col and pd.notna(row[war_no_col]) else None
        raw_chq = row[chq_no_col] if chq_no_col and pd.notna(row[chq_no_col]) else None
        
        parsed_war = to_int(raw_war)
        parsed_chq = to_int(raw_chq)
        
        def is_empty_val(v):
            if v is None:
                return True
            s = str(v).strip()
            return s == "" or s.lower() in ["nan", "none"]
            
        if war_no_col and chq_no_col:
            # Case 1: if splitting WAR_NO gives two values and CHQ_NO is empty
            if not is_empty_val(raw_war):
                war_str = str(raw_war).strip()
                war_parts = war_str.split()
                if len(war_parts) == 2 and is_empty_val(raw_chq):
                    parsed_war = to_int(war_parts[0])
                    parsed_chq = to_int(war_parts[1])
            # Case 2: if WAR_NO is empty and CHQ_NO has data
            elif is_empty_val(raw_war) and not is_empty_val(raw_chq):
                chq_str = str(raw_chq).strip()
                chq_parts = chq_str.split()
                if len(chq_parts) == 2:
                    parsed_war = to_int(chq_parts[0])
                    parsed_chq = to_int(chq_parts[1])

        record = {
            'folio_id': raw_folio if raw_folio else None,
            'name': str(names.iloc[idx]).strip() if pd.notna(names.iloc[idx]) else "",
            'address': str(addresses.iloc[idx]).strip() if pd.notna(addresses.iloc[idx]) else None,
            'pin_code': to_int(row[pin_code_col]) if pin_code_col else None,
            'number_of_shares': to_int(row[shares_col]) if shares_col else None,
            'net_dividend': to_float(row[dividend_col]) if dividend_col else None,
            'war_no': parsed_war,
            'chq_no': parsed_chq
        }
        
        # Avoid records with blank names (database constraint)
        if record['name'] and record['name'].lower() not in ['nan', 'none', '']:
            records.append(record)
            
    return records
