"""
check_splits_and_missing.py - Diagnose remaining geography issues.
"""
import pandas as pd
from boundaries import BOUNDARY_SPLITS, combine_splits

sfc = pd.read_csv('data/intermediate/england_panel_sfc.csv')
rama = pd.read_stata('data/rama.dta')

sfc_w = sfc.drop_duplicates(subset=['la_code','year'])
rama_w = rama.drop_duplicates(subset=['local_auth'])

# Check BOUNDARY_SPLITS definition
print('BOUNDARY_SPLITS defined in boundaries.py:')
for code, info in BOUNDARY_SPLITS.items():
    print(f'  {code}: {info["split_parts"]}')
print()

# Check which split parts are in our panel
print('Split parts in SfC panel:')
all_parts = [p for info in BOUNDARY_SPLITS.values() for p in info['split_parts']]
for code in all_parts:
    present = code in sfc_w['la_code'].values
    print(f'  {code}: {"PRESENT" if present else "absent"}')
print()

# Check North Yorkshire and Somerset
print('2023 merged authorities:')
for code, name in [('E06000065','North Yorkshire'),
                   ('E06000066','Somerset')]:
    present = code in sfc_w['la_code'].values
    rama_present = name.lower() in rama_w['local_auth'].str.lower().values
    print(f'  {code} {name}: ours={"PRESENT" if present else "ABSENT"}, '
          f'rama={"PRESENT" if rama_present else "absent"}')
print()

# Check what columns the sfc panel has
print('Columns in SfC panel:')
print(sfc.columns.tolist())
print()

# Total LAs
print(f'Total LAs in our panel: {sfc_w["la_code"].nunique()}')
print(f'Total LAs in Ramas:     {rama_w["local_auth"].nunique()}')
