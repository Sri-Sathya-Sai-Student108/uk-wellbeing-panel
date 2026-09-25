"""
check_geolytix.py - Sanity check Geolytix file discovery and store counts.

Run from project root:
  python check_geolytix.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import os
import re
import pandas as pd
from config import DATA_DIR

GEOLYTIX_DIR = os.path.join(DATA_DIR, 'geolytix')

DISCOUNTERS = {'Aldi', 'Lidl'}
INCUMBENTS  = {'Tesco', 'Asda', 'Sainsburys', 'Morrisons',
               'Iceland', 'Marks and Spencer', 'Waitrose'}
EXCLUDE     = {'Asda PFS', 'Marks and Spencer BP', 'Marks and Spencer MSA',
               'Tesco Express Esso', 'Waitrose MSA', 'Little Waitrose Shell'}

ALL_RETAILERS = DISCOUNTERS | INCUMBENTS


def parse_filename(fname):
    m = re.match(r'geolytix_retailpoints_v(\d+)_(\d{4})(\d{2})\.csv',
                 fname, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def find_latest_per_year(geolytix_dir, year_min=2016, year_max=2023):
    candidates = {}
    for fname in os.listdir(geolytix_dir):
        parsed = parse_filename(fname)
        if not parsed:
            continue
        version, year, month = parsed
        if not (year_min <= year <= year_max):
            continue
        if year not in candidates or (month, version) > (candidates[year][1], candidates[year][0]):
            candidates[year] = (version, month, fname)
    return {y: fp for y, (_, _, fp) in sorted(candidates.items())}


print("=" * 60)
print("GEOLYTIX DIAGNOSTIC CHECK")
print("=" * 60)

# Check directory exists
if not os.path.isdir(GEOLYTIX_DIR):
    print(f"\nERROR: Directory not found: {GEOLYTIX_DIR}")
    print("Create it and copy Geolytix CSV files there.")
    raise SystemExit(1)

# List all files found
all_files = [f for f in os.listdir(GEOLYTIX_DIR)
             if f.lower().endswith('.csv')]
print(f"\nAll CSV files in {GEOLYTIX_DIR}: {len(all_files)}")

# File discovery
print("\nFiles selected per study year (2016-2023):")
file_map = find_latest_per_year(GEOLYTIX_DIR)

if not file_map:
    print("  ERROR: No files found for 2016-2023.")
    print("  Check files are named: geolytix_retailpoints_vN_YYYYMM.csv")
    raise SystemExit(1)

for year in sorted(file_map):
    print(f"  {year}: {file_map[year]}")

missing_years = set(range(2016, 2024)) - set(file_map)
if missing_years:
    print(f"\n  WARNING: No files found for years: {sorted(missing_years)}")
else:
    print(f"\n  All 8 study years covered.")

# Count check on each year
print("\n" + "=" * 60)
print("STORE COUNTS BY YEAR")
print("=" * 60)
print(f"{'Year':<6} {'File':<45} {'Total':>7} {'Disc':>6} {'Incumb':>7}")
print("-" * 75)

for year in sorted(file_map):
    fpath = os.path.join(GEOLYTIX_DIR, file_map[year])
    df = pd.read_csv(fpath, low_memory=False)
    df.columns = df.columns.str.lower().str.strip()

    # Standardise column name variations
    if 'retailer' not in df.columns:
        print(f"  {year}: WARNING - no 'retailer' column. Columns: {list(df.columns)}")
        continue

    df = df[df['retailer'].isin(ALL_RETAILERS)]
    df = df[~df['fascia'].isin(EXCLUDE)]

    tot     = len(df)
    tot_new = df['retailer'].isin(DISCOUNTERS).sum()
    tot_old = df['retailer'].isin(INCUMBENTS).sum()

    print(f"  {year}  {file_map[year]:<43} {tot:>7,} {tot_new:>6,} {tot_old:>7,}")

# Detailed breakdown for 2016 baseline
print()
print("=" * 60)
print("2016 BASELINE - RETAILER BREAKDOWN")
print("=" * 60)
if 2016 in file_map:
    fpath = os.path.join(GEOLYTIX_DIR, file_map[2016])
    df = pd.read_csv(fpath, low_memory=False)
    df.columns = df.columns.str.lower().str.strip()
    df = df[df['retailer'].isin(ALL_RETAILERS)]
    df = df[~df['fascia'].isin(EXCLUDE)]

    print(f"\nFile: {file_map[2016]}")
    print(f"\nBy retailer:")
    counts = df['retailer'].value_counts()
    for retailer, n in counts.items():
        tag = ' [DISCOUNTER]' if retailer in DISCOUNTERS else ''
        print(f"  {retailer:<30} {n:>5,}{tag}")

    print(f"\nExcluded fascias present in file:")
    df_all = pd.read_csv(fpath, low_memory=False)
    df_all.columns = df_all.columns.str.lower().str.strip()
    df_all = df_all[df_all['retailer'].isin(ALL_RETAILERS)]
    excluded = df_all[df_all['fascia'].isin(EXCLUDE)]
    if len(excluded) > 0:
        print(excluded['fascia'].value_counts().to_string())
    else:
        print("  None found (fascia names may differ in older files)")

print("\nDone.")
