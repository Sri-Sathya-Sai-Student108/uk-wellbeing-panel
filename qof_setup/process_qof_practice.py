#!/usr/bin/env python3
"""
process_qof_practice.py — Aggregate QOF practice-level prevalence to LA level.

Pipeline:
  1. Load GP practice registry (epraccur) to get practice postcodes
  2. Load ONS postcode lookup (NSPL) to map postcodes to lower-tier LAs
  3. Build practice -> LA lookup
  4. For each year's QOF cardiovascular practice file:
     a. Extract hypertension register count and list size per practice
     b. Join to LA via the lookup
     c. Aggregate to LA: sum(register) / sum(list_size) * 100 = prevalence %
  5. Output a single panel CSV: la_code, year, qof_prevalence

Usage:
  python process_qof_practice.py                    # process all available years
  python process_qof_practice.py --year 2022        # process just one year
  python process_qof_practice.py --check            # check what files are available
  python process_qof_practice.py --condition HYP001 # hypertension (default)
  python process_qof_practice.py --condition DM001   # diabetes instead

Output:
  data/qof_hypertension_la.csv  (or qof_diabetes_la.csv)
  This file plugs directly into qof_panel.py as the QOF data source.
"""

import argparse
import glob
import os
import sys
import warnings
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
QOF_DIR = os.path.join(DATA_DIR, "qof_practice")

# QOF indicator codes for the conditions we care about
CONDITIONS = {
    'HYP001': {'name': 'hypertension', 'label': 'Hypertension'},
    'DM001':  {'name': 'diabetes', 'label': 'Diabetes (17+)'},
}


# ============================================================================
# STEP 1: Build practice -> LA lookup
# ============================================================================

def build_practice_la_lookup():
    """
    Join epraccur (practice postcodes) to NSPL (postcode -> LA) to create
    a practice_code -> la_code mapping.
    
    Returns DataFrame with: practice_code, la_code, postcode
    """
    # ---- Load epraccur ----
    epraccur_path = os.path.join(DATA_DIR, 'epraccur.csv')
    if not os.path.exists(epraccur_path):
        print(f"ERROR: {epraccur_path} not found.")
        print("  Download from: https://digital.nhs.uk/services/organisation-data-service/"
              "export-data-files/csv-downloads/gp-and-gp-practice-related-data")
        return None
    
    print("Loading GP practice registry (epraccur)...")
    # epraccur has no header row — columns are positional
    # Col 0: Organisation Code, Col 1: Name, ..., Col 9: Postcode, Col 12: Status
    # But format varies. Try with and without headers.
    try:
        epr = pd.read_csv(epraccur_path, header=None, dtype=str, 
                           on_bad_lines='skip')
        # Practice code is col 0, postcode is col 9 (typically)
        # Check if first row looks like a header
        if epr.iloc[0, 0] in ['Organisation Code', 'Organisation_Code', 
                                'org_code', 'Code']:
            epr.columns = epr.iloc[0]
            epr = epr.iloc[1:]
        
        # Find practice code column (6 chars starting with letter)
        code_col = None
        pc_col = None
        for i, col in enumerate(epr.columns):
            sample = epr.iloc[:20, i].dropna().astype(str)
            # Practice codes: letter + 5 digits (e.g. A81001)
            if code_col is None and sample.str.match(r'^[A-Z]\d{5}$').mean() > 0.5:
                code_col = i
            # Postcodes: letter(s) + digit(s) + space + digit + letters
            if pc_col is None and sample.str.match(r'^[A-Z]{1,2}\d').mean() > 0.3:
                pc_col = i
        
        if code_col is None or pc_col is None:
            # Fallback: col 0 = code, col 9 = postcode (standard epraccur layout)
            code_col = 0
            pc_col = 9
            print(f"  Using positional columns: code={code_col}, postcode={pc_col}")
        
        practices = pd.DataFrame({
            'practice_code': epr.iloc[:, code_col].astype(str).str.strip(),
            'postcode': epr.iloc[:, pc_col].astype(str).str.strip().str.upper(),
        })
        
    except Exception as e:
        print(f"  Error reading epraccur: {e}")
        return None
    
    # Clean postcodes — remove spaces for matching
    practices['pc_clean'] = practices['postcode'].str.replace(' ', '')
    practices = practices[practices['practice_code'].str.match(r'^[A-Z]\d{5}$', na=False)]
    print(f"  {len(practices)} practices with valid codes")
    
    # ---- Load NSPL ----
    nspl_path = os.path.join(DATA_DIR, 'nspl.csv')
    onspd_path = os.path.join(DATA_DIR, 'onspd.csv')
    
    pc_path = nspl_path if os.path.exists(nspl_path) else onspd_path
    if not os.path.exists(pc_path):
        print(f"ERROR: Neither {nspl_path} nor {onspd_path} found.")
        print("  Download NSPL from: https://geoportal.statistics.gov.uk/search?q=nspl")
        return None
    
    print(f"Loading postcode lookup ({os.path.basename(pc_path)})...")
    # NSPL is large — only read the columns we need
    # Try to detect column names first
    header = pd.read_csv(pc_path, nrows=0)
    cols = list(header.columns)
    cols_lower = [c.lower() for c in cols]
    
    # Find postcode column and LA column
    pc_col_name = None
    la_col_name = None
    for c, cl in zip(cols, cols_lower):
        if cl in ['pcds', 'pcd', 'postcode', 'pcd2']:
            pc_col_name = c
        if cl in ['laua', 'oslaua', 'ladcd', 'la_code']:
            la_col_name = c
    
    if not pc_col_name or not la_col_name:
        print(f"  Could not find postcode/LA columns in: {cols[:15]}...")
        print(f"  Trying 'pcds' and 'laua' as defaults")
        pc_col_name = 'pcds'
        la_col_name = 'laua'
    
    print(f"  Reading columns: {pc_col_name}, {la_col_name}")
    nspl = pd.read_csv(pc_path, usecols=[pc_col_name, la_col_name], dtype=str)
    nspl = nspl.rename(columns={pc_col_name: 'postcode', la_col_name: 'la_code'})
    nspl['pc_clean'] = nspl['postcode'].str.replace(' ', '').str.upper()
    nspl = nspl.dropna(subset=['la_code'])
    print(f"  {len(nspl)} postcodes loaded")
    
    # ---- Join ----
    lookup = practices.merge(nspl[['pc_clean', 'la_code']], on='pc_clean', how='left')
    matched = lookup['la_code'].notna().sum()
    print(f"  Matched {matched}/{len(lookup)} practices to LAs "
          f"({matched/len(lookup)*100:.1f}%)")
    
    lookup = lookup[lookup['la_code'].notna()]
    return lookup[['practice_code', 'la_code', 'postcode']].copy()


# ============================================================================
# STEP 2: Load and parse QOF practice-level file for one year
# ============================================================================

def load_qof_year(year, condition='HYP001'):
    """
    Load QOF cardiovascular practice-level file for a given year.
    Extract the hypertension (or diabetes) register count and list size.
    
    Returns DataFrame with: practice_code, register, list_size
    """
    # Find the file
    base = os.path.join(QOF_DIR, f'qof_cardio_{year}')
    filepath = None
    for ext in ['.csv', '.xlsx', '.xls', '.CSV', '.XLSX']:
        candidate = base + ext
        if os.path.exists(candidate):
            filepath = candidate
            break
    
    # Also check for any file containing the year
    if filepath is None:
        pattern = os.path.join(QOF_DIR, f'*{year}*')
        matches = glob.glob(pattern)
        if matches:
            filepath = matches[0]
    
    if filepath is None:
        return None
    
    print(f"  Loading {os.path.basename(filepath)}...")
    
    # Read the file
    try:
        if filepath.lower().endswith('.csv'):
            df = pd.read_csv(filepath, dtype=str, low_memory=False,
                              on_bad_lines='skip')
        else:
            # XLSX/XLS — try different sheets
            df = None
            xls = pd.ExcelFile(filepath)
            for sheet in xls.sheet_names:
                trial = pd.read_excel(filepath, sheet_name=sheet, dtype=str)
                # Look for sheet with practice codes
                for c in trial.columns[:5]:
                    if trial[c].dropna().astype(str).str.match(r'^[A-Z]\d{5}$').any():
                        df = trial
                        break
                if df is not None:
                    break
            if df is None:
                df = pd.read_excel(filepath, dtype=str)
    except Exception as e:
        print(f"    Error reading file: {e}")
        return None
    
    df.columns = df.columns.str.strip()
    
    # Find practice code column
    code_col = None
    for c in df.columns:
        cl = c.lower()
        if 'practice' in cl and 'code' in cl:
            code_col = c
            break
        if cl in ['practice_code', 'org_code', 'organisation_code']:
            code_col = c
            break
    if code_col is None:
        for c in df.columns:
            if df[c].dropna().astype(str).str.match(r'^[A-Z]\d{5}$').mean() > 0.3:
                code_col = c
                break
    
    if code_col is None:
        print(f"    Can't find practice code column. Columns: {list(df.columns)[:10]}")
        return None
    
    # Find the register/indicator column
    # We need the register count for our condition and the list size
    # The file structure varies by year. Common patterns:
    # - Column per indicator with register counts
    # - Long format with indicator code, register, list_size columns
    
    # Check if it's long format (has an indicator code column)
    indicator_col = None
    for c in df.columns:
        cl = c.lower()
        if 'indicator' in cl and ('code' in cl or 'id' in cl or cl == 'indicator'):
            indicator_col = c
            break
        if cl in ['ind_code', 'indicator_code', 'indicator_group_ind_code']:
            indicator_col = c
            break
    
    register_col = None
    listsize_col = None
    
    if indicator_col:
        # Long format — filter to our condition
        df_cond = df[df[indicator_col].str.upper().str.strip() == condition]
        if len(df_cond) == 0:
            # Try partial match
            df_cond = df[df[indicator_col].str.contains(condition[:3], case=False, na=False)]
        
        if len(df_cond) == 0:
            print(f"    Condition {condition} not found in indicator column")
            print(f"    Available: {df[indicator_col].unique()[:20]}")
            return None
        
        # Find register and list size columns
        for c in df_cond.columns:
            cl = c.lower()
            if 'register' in cl or 'numerator' in cl:
                register_col = c
            if 'list' in cl and 'size' in cl:
                listsize_col = c
            if cl in ['register', 'prevalence_numerator']:
                register_col = c
            if cl in ['list_size_all', 'list_size']:
                listsize_col = c
        
        if register_col and listsize_col:
            result = pd.DataFrame({
                'practice_code': df_cond[code_col].astype(str).str.strip(),
                'register': pd.to_numeric(df_cond[register_col], errors='coerce'),
                'list_size': pd.to_numeric(df_cond[listsize_col], errors='coerce'),
            })
            result = result.dropna(subset=['register', 'list_size'])
            result = result[result['list_size'] > 0]
            print(f"    {len(result)} practices with {condition} data")
            return result
    
    # Wide format or can't find indicator column — look for HYP/DM columns
    for c in df.columns:
        cl = c.lower()
        if condition.lower()[:3] in cl and ('register' in cl or 'reg' in cl 
                                              or 'numerator' in cl):
            register_col = c
        if 'list' in cl and 'size' in cl and ('all' in cl or 'total' in cl 
                                                or cl == 'list_size'):
            listsize_col = c
    
    # If still no list size, look for any list size column
    if listsize_col is None:
        for c in df.columns:
            cl = c.lower()
            if 'list' in cl and 'size' in cl:
                listsize_col = c
                break
    
    if register_col is None or listsize_col is None:
        print(f"    Can't find register/list_size columns for {condition}")
        print(f"    Columns: {list(df.columns)}")
        print(f"    Register col: {register_col}, List size col: {listsize_col}")
        return None
    
    result = pd.DataFrame({
        'practice_code': df[code_col].astype(str).str.strip(),
        'register': pd.to_numeric(df[register_col], errors='coerce'),
        'list_size': pd.to_numeric(df[listsize_col], errors='coerce'),
    })
    result = result.dropna(subset=['register', 'list_size'])
    result = result[result['list_size'] > 0]
    print(f"    {len(result)} practices with {condition} data")
    return result


# ============================================================================
# STEP 3: Aggregate to LA level
# ============================================================================

def aggregate_to_la(practice_df, lookup_df, year):
    """
    Join practice data to LA lookup, aggregate by LA.
    
    Prevalence = sum(register) / sum(list_size) * 100
    """
    merged = practice_df.merge(lookup_df[['practice_code', 'la_code']],
                                on='practice_code', how='inner')
    
    unmatched = len(practice_df) - len(merged)
    if unmatched > 0:
        print(f"    {unmatched} practices not matched to LA "
              f"({unmatched/len(practice_df)*100:.1f}%)")
    
    la = merged.groupby('la_code').agg(
        register_total=('register', 'sum'),
        list_size_total=('list_size', 'sum'),
        n_practices=('practice_code', 'count'),
    ).reset_index()
    
    la['qof_prevalence'] = (la['register_total'] / la['list_size_total']) * 100
    la['year'] = year
    
    print(f"    Aggregated to {len(la)} LAs "
          f"(mean prevalence: {la['qof_prevalence'].mean():.1f}%)")
    
    return la[['la_code', 'year', 'qof_prevalence', 'n_practices',
               'register_total', 'list_size_total']].copy()


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Aggregate QOF practice data to LA level')
    parser.add_argument('--year', type=int,
                        help='Process just one year')
    parser.add_argument('--condition', default='HYP001',
                        choices=list(CONDITIONS.keys()),
                        help='QOF condition code (default: HYP001 hypertension)')
    parser.add_argument('--check', action='store_true',
                        help='Check which files are available')
    args = parser.parse_args()
    
    cond = CONDITIONS[args.condition]
    
    if args.check:
        print(f"Checking for QOF files in {QOF_DIR}/...")
        years_found = []
        for year in range(2012, 2023):
            base = os.path.join(QOF_DIR, f'qof_cardio_{year}')
            found = any(os.path.exists(base + ext) 
                       for ext in ['.csv', '.xlsx', '.xls'])
            if not found:
                matches = glob.glob(os.path.join(QOF_DIR, f'*{year}*'))
                found = len(matches) > 0
            status = "OK" if found else "MISSING"
            print(f"  [{status:7s}] {year}-{year+1-2000:02d}")
            if found:
                years_found.append(year)
        
        print(f"\n{len(years_found)}/{11} years found")
        print(f"\nepraccur.csv: {'OK' if os.path.exists(os.path.join(DATA_DIR, 'epraccur.csv')) else 'MISSING'}")
        print(f"nspl.csv: {'OK' if os.path.exists(os.path.join(DATA_DIR, 'nspl.csv')) else 'MISSING'}")
        return
    
    print("=" * 60)
    print(f"QOF PRACTICE-TO-LA AGGREGATION")
    print(f"  Condition: {args.condition} ({cond['label']})")
    print("=" * 60)
    
    # Build practice -> LA lookup
    lookup = build_practice_la_lookup()
    if lookup is None:
        return
    
    # Process each year
    years = [args.year] if args.year else list(range(2012, 2023))
    
    all_la = []
    for year in years:
        print(f"\n--- {year}-{year+1-2000:02d} ---")
        practice_df = load_qof_year(year, condition=args.condition)
        if practice_df is None:
            print(f"  Skipping {year} (no data)")
            continue
        
        la_df = aggregate_to_la(practice_df, lookup, year)
        all_la.append(la_df)
    
    if not all_la:
        print("\nNo data processed.")
        return
    
    # Combine all years
    panel = pd.concat(all_la, ignore_index=True)
    
    # Save
    output_name = f'qof_{cond["name"]}_la.csv'
    output_path = os.path.join(DATA_DIR, output_name)
    panel.to_csv(output_path, index=False)
    
    print(f"\n{'=' * 60}")
    print(f"DONE")
    print(f"  Output: {output_path}")
    print(f"  {panel['la_code'].nunique()} LAs, {len(panel)} observations")
    print(f"  Years: {sorted(panel['year'].unique())}")
    print(f"  Mean prevalence: {panel['qof_prevalence'].mean():.2f}%")
    print(f"\nThis file plugs into qof_panel.py:")
    print(f"  python qof_panel.py  (it will auto-detect {output_name})")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
