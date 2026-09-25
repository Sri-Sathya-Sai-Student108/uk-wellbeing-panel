"""
check_claimant_codes.py - Diagnose LA code formats in claimant count file.
"""
import pandas as pd

cc  = pd.read_csv('data/intermediate/claimant_count_annual.csv')
pop = pd.read_csv('data/intermediate/population_annual.csv')

print('CLAIMANT COUNT CODES')
print('=' * 50)
print(f'Total LAs: {cc["la_code"].nunique()}')
print(f'Sample codes:')
sample = cc[['la_code','la_name']].drop_duplicates().head(20)
print(sample.to_string())

print()
print('CODE PREFIX DISTRIBUTION')
cc_eng = cc[cc['la_code'].str.startswith('E', na=False)]
prefixes = cc_eng['la_code'].str[:4].value_counts().sort_index()
print(prefixes.to_string())

print()
print('POPULATION CODES')
print('=' * 50)
print(f'Total LAs: {pop["la_code"].nunique()}')
print(f'Sample codes:')
sample2 = pop[['la_code','la_name']].drop_duplicates().head(10)
print(sample2.to_string())

print()
print('CODE PREFIX DISTRIBUTION (population)')
pop_eng = pop[pop['la_code'].str.startswith('E', na=False)]
prefixes2 = pop_eng['la_code'].str[:4].value_counts().sort_index()
print(prefixes2.to_string())

print()
print('OVERLAP CHECK')
cc_codes  = set(cc['la_code'].unique())
pop_codes = set(pop['la_code'].unique())
both = cc_codes & pop_codes
print(f'Codes in both files: {len(both)}')
print(f'In claimants only:   {len(cc_codes - pop_codes)}')
print(f'In population only:  {len(pop_codes - cc_codes)}')
if both:
    print(f'Sample matching codes: {sorted(list(both))[:5]}')
