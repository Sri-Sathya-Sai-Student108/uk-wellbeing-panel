"""
check_claimant_codes2.py - Verify claimant count codes after fix.
"""
import pandas as pd

cc  = pd.read_csv('data/intermediate/claimant_count_annual.csv')
pop = pd.read_csv('data/intermediate/population_annual.csv')

print('CLAIMANT COUNT AFTER FIX')
print(f'Total LAs: {cc["la_code"].nunique()}')
print(f'Code prefixes:')
print(cc['la_code'].str[:4].value_counts().sort_index().to_string())
print()
print('Sample codes:')
print(cc[['la_code','la_name']].drop_duplicates().head(10).to_string())
print()

cc_codes  = set(cc['la_code'].unique())
pop_codes = set(pop['la_code'].unique())
both = cc_codes & pop_codes
print(f'Overlap with population file: {len(both)} LAs')
print(f'In claimants only: {len(cc_codes - pop_codes)}')
print(f'In population only: {len(pop_codes - cc_codes)}')
