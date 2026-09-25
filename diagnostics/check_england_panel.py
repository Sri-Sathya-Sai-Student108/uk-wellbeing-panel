"""
check_england_panel.py - Sanity check on assembled England base panel.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

df = pd.read_csv('data/intermediate/england_panel_base.csv')

print('ENGLAND BASE PANEL')
print('=' * 60)
print(f'Observations: {len(df):,}')
print(f'LAs:          {df["la_code"].nunique()}')
print(f'Years:        {sorted(df["year"].unique())}')
print(f'Measures:     {sorted(df["measure"].dropna().unique())}')
print(f'Regions:      {sorted(df["region"].dropna().unique())}')

print()
print('DESCRIPTIVE STATISTICS (2020-2023, life-satisfaction)')
ls = df[(df['measure'] == 'life-satisfaction') &
        (df['year'] >= 2020)]
print(ls[['claimants_mean','pop_total','pop_65plus',
          'overseas_share','value']].describe().round(3).to_string())

print()
print('OVERSEAS SHARE BY REGION (2020-2023 mean):')
reg = df[(df['year'] >= 2020)].groupby('region')['overseas_share'].mean()
print(reg.sort_values(ascending=False).round(3).to_string())

print()
print('SAMPLE ROWS:')
print(df[df['la_code'] == 'E08000021'][
    ['la_code','la_name','year','measure','value',
     'claimants_mean','pop_total','overseas_share']
].head(8).to_string())
