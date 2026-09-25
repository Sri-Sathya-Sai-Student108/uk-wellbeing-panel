"""
check_missing_overlap.py - Find population LAs not in claimant count.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

cc  = pd.read_csv('data/intermediate/claimant_count_annual.csv')
pop = pd.read_csv('data/intermediate/population_annual.csv')

cc_codes  = set(cc['la_code'].unique())
pop_codes = set(pop['la_code'].unique())

missing_from_cc = pop_codes - cc_codes
pop_lads = pop[['la_code','la_name']].drop_duplicates()

print('Population LAs not in claimant count:')
missing = pop_lads[pop_lads['la_code'].isin(missing_from_cc)].sort_values('la_code')
print(missing.to_string())
print(f'\nTotal: {len(missing)}')

print()
print('Claimants LAs not in population (E/S codes only):')
cc_lads = cc[['la_code','la_name']].drop_duplicates()
cc_only = cc_lads[cc_lads['la_code'].isin(cc_codes - pop_codes)]
cc_only = cc_only[cc_only['la_code'].str.match(r'^[ES]')]
print(cc_only.sort_values('la_code').to_string())
