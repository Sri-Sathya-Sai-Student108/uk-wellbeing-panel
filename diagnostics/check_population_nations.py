"""
check_population_nations.py - Check which nations are in the population file.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

df = pd.read_csv('data/intermediate/population_annual.csv')

print('LA code prefixes (one row per year per LA):')
print(df['la_code'].str[:1].value_counts())

print()
print('Unique LAs by nation:')
lads = df[['la_code', 'la_name']].drop_duplicates()
for prefix, nation in [('E', 'England'), ('W', 'Wales'),
                        ('S', 'Scotland'), ('N', 'Northern Ireland')]:
    n = lads[lads['la_code'].str.startswith(prefix, na=False)]
    print(f'  {nation} ({prefix}): {len(n)} LAs')

print()
nulls = df[df['la_code'].isna()]['la_name'].unique()
print(f'LAs with no code matched ({len(nulls)}):')
for n in sorted(nulls)[:20]:
    print(f'  {n}')
