"""
check_claimants_discrepancy.py - Why are our claimant counts 25% lower than Rama's?
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

r = pd.read_stata('data/rama.dta')
ours = pd.read_csv('data/intermediate/england_panel_sfc.csv')
ours = ours.drop_duplicates(subset=['la_code','year'])

# Match by LA name
r['la_name_lower']    = r['local_auth'].str.strip().str.lower()
ours['la_name_lower'] = ours['la_name'].str.strip().str.lower()

for year in [2020, 2021, 2022, 2023]:
    yr_ours = ours[ours['year']==year]
    yr_rama = r[r['year']==year]

    merged = yr_ours.merge(
        yr_rama[['la_name_lower','benefit_claimants','pop_all']],
        on='la_name_lower', how='inner'
    )

    ratio = merged['claimants_mean'] / merged['benefit_claimants']
    print(f'Year {year} ({len(merged)} matched LAs):')
    print(f'  Our claimants mean:   {merged["claimants_mean"].mean():,.0f}')
    print(f'  Rama claimants mean:  {merged["benefit_claimants"].mean():,.0f}')
    print(f'  Ratio (ours/rama):    {ratio.mean():.3f}')
    print(f'  Our pop_total mean:   {merged["pop_total"].mean():,.0f}')
    print(f'  Rama pop_all mean:    {merged["pop_all"].mean():,.0f}')
    print()

# Check national totals
print('NATIONAL CLAIMANT TOTALS:')
for year in [2020,2021,2022,2023]:
    ours_tot = ours[ours['year']==year]['claimants_mean'].sum()
    rama_tot = r[r['year']==year]['benefit_claimants'].sum()
    print(f'  {year}: ours={ours_tot:,.0f}  rama={rama_tot:,.0f}  '
          f'ratio={ours_tot/rama_tot:.3f}')
