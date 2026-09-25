"""
check_sfc_geography.py - Check what geographic codes are in the SfC panel.
"""
import pandas as pd

sfc = pd.read_csv('data/intermediate/england_panel_sfc.csv')
lad_cty = pd.read_csv('data/lad_to_county.csv')

sfc_w = sfc.drop_duplicates(subset=['la_code', 'year'])

print('CODE PREFIX DISTRIBUTION IN SFC PANEL:')
print(sfc_w['la_code'].str[:4].value_counts().sort_index().to_string())
print()

# E07 districts that should have been aggregated
e07 = sfc_w[sfc_w['la_code'].str.startswith('E07')]
print(f'E07 districts in SfC panel: {e07["la_code"].nunique()}')
if len(e07) > 0:
    print(e07[['la_code','la_name']].drop_duplicates().to_string())
print()

# Split codes that should be combined
split_codes = ['E06000063','E06000064',  # Cumbria
               'E06000061','E06000062',  # Northants
               'E06000058','E06000059']  # Dorset
splits = sfc_w[sfc_w['la_code'].isin(split_codes)]
print(f'Split codes still separate: {splits["la_code"].nunique()}')
if len(splits) > 0:
    print(splits[['la_code','la_name']].drop_duplicates().to_string())
print()

# Combined codes
combined = sfc_w[sfc_w['la_code'].isin(
    ['DORSET_COMBINED','NORTHANTS_COMBINED','CUMBRIA_COMBINED'])]
print(f'Combined codes present: {combined["la_code"].nunique()}')
if len(combined) > 0:
    print(combined[['la_code','la_name']].drop_duplicates().to_string())
print()

# Total unique LAs
print(f'Total unique LAs in SfC panel: {sfc_w["la_code"].nunique()}')
print(f'Expected: ~150 upper-tier LAs')
