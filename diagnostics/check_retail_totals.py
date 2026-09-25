"""
check_retail_totals.py - Check national retail totals match across geographies.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

retail_eng = pd.read_csv('data/intermediate/retail_data_england.csv')
panel_sfc  = pd.read_csv('data/intermediate/england_panel_sfc.csv')

# Deduplicate panel to one row per LA-year
panel_wide = panel_sfc.drop_duplicates(subset=['la_code','year'])

print('NATIONAL RETAIL TOTALS BY YEAR')
print('=' * 60)
print(f'{"Year":<6} {"Lower-tier (retail_eng)":>25} {"Upper-tier (panel_sfc)":>25}')
print('-' * 60)
for year in sorted(retail_eng['year'].unique()):
    lt = retail_eng[retail_eng['year']==year]['tot'].sum()
    ut_row = panel_wide[panel_wide['year']==year]['tot']
    ut = ut_row.sum()
    print(f'{year:<6} {lt:>25,.0f} {ut:>25,.0f}')

print()
print('LA COUNTS BY YEAR')
print(f'{"Year":<6} {"Lower-tier LAs":>20} {"Upper-tier LAs":>20}')
print('-' * 48)
for year in sorted(retail_eng['year'].unique()):
    lt = retail_eng[retail_eng['year']==year]['la_code'].nunique()
    ut = panel_wide[panel_wide['year']==year]['la_code'].nunique()
    print(f'{year:<6} {lt:>20} {ut:>20}')
