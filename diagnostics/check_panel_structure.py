"""
check_panel_structure.py - Verify panel structure after all joins.
"""
import pandas as pd

sfc = pd.read_csv('data/intermediate/england_panel_sfc.csv')
base = pd.read_csv('data/intermediate/england_panel_base.csv')

print('ENGLAND SFC PANEL')
print('='*50)
print(f'Rows: {len(sfc):,}')
print(f'LAs: {sfc["la_code"].nunique()}')
print(f'Years: {sorted(sfc["year"].unique())}')
print(f'Rows per LA per year (should be 4 for 4 measures):')
counts = sfc.groupby(['la_code','year']).size()
print(counts.value_counts().to_string())
print()
print(f'Overseas share - unique values: {sfc["overseas_share"].nunique()}')
print(f'(Should be 9 x 8 = 72 unique values if regional)')
print()
print('Sample - same LA different years:')
sample = sfc[sfc['la_code']=='E08000021'][
    ['la_code','la_name','year','region','overseas_share',
     'tot','claimants_mean','filled_posts']
].drop_duplicates(subset=['la_code','year']).head(8)
print(sample.to_string())
print()
print('ENGLAND BASE PANEL')
print('='*50)
print(f'Rows: {len(base):,}')
print(f'LAs: {base["la_code"].nunique()}')
print(f'Years: {sorted(base["year"].unique())}')
