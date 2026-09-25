"""
check_panel.py - Check completeness of all intermediate panel datasets.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import os

print('=' * 60)
print('PANEL DATA COMPLETENESS CHECK')
print('=' * 60)

files = {
    'Retail England':  'data/intermediate/retail_data_england.csv',
    'Retail Scotland': 'data/intermediate/retail_data_scotland.csv',
    'Claimant Count':  'data/intermediate/claimant_count_annual.csv',
    'Population':      'data/intermediate/population_annual.csv',
}

for name, path in files.items():
    if not os.path.exists(path):
        print(f'\n{name}: FILE NOT FOUND ({path})')
        continue

    df = pd.read_csv(path)
    print(f'\n{name}:')
    print(f'  Rows:  {len(df):,}')

    if 'la_code' in df.columns:
        print(f'  LAs:   {df["la_code"].nunique()}')
    if 'year' in df.columns:
        print(f'  Years: {sorted(df["year"].unique())}')

    # Missing values
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        print(f'  Missing values:')
        for col, n in missing.items():
            pct = n / len(df) * 100
            print(f'    {col}: {n} ({pct:.1f}%)')
    else:
        print(f'  Missing values: none')

    # Panel balance check
    if 'la_code' in df.columns and 'year' in df.columns:
        counts  = df.groupby('la_code')['year'].count()
        n_years = df['year'].nunique()
        min_yrs = counts.min()
        max_yrs = counts.max()
        if min_yrs == max_yrs == n_years:
            print(f'  Balance: BALANCED '
                  f'({n_years} years x {df["la_code"].nunique()} LAs)')
        else:
            print(f'  Balance: UNBALANCED '
                  f'(min {min_yrs}, max {max_yrs} years per LA)')
            short = counts[counts < n_years]
            print(f'  LAs with incomplete series: {len(short)}')
            for la, n in short.head(10).items():
                la_name = df[df['la_code'] == la]['la_name'].iloc[0] \
                          if 'la_name' in df.columns else ''
                print(f'    {la} {la_name}: {n} years')

print()
print('=' * 60)
