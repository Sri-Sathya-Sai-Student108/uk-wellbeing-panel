"""
compare_panels.py - Direct comparison of our panel vs Rama's Stata panel.
Run from project root with rama.dta in project root.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

# Load both panels
rama = pd.read_stata('data/rama.dta')
ours = pd.read_csv('data/intermediate/england_panel_sfc.csv')
ours = ours.drop_duplicates(subset=['la_code','year'])
ours = ours[~ours['la_code'].isin({'E09000001','E06000053'})]

# Rebuild bartik on our panel (without leave-one-out for simplicity)
base = ours[ours['year']==2016][['la_code','la_name','tot_new','tot_old','tot']].copy()
base['share_new'] = base['tot_new'] / base['tot']
ours = ours.merge(base[['la_code','share_new']], on='la_code')
nat = ours.groupby('year')[['tot_new','tot_old']].sum().reset_index()
nat.columns = ['year','nat_new','nat_old']
ours = ours.merge(nat, on='year')
base_nat = ours[ours['year']==2016][['la_code','nat_new','nat_old']].rename(
    columns={'nat_new':'base_nat_new','nat_old':'base_nat_old'})
ours = ours.merge(base_nat, on='la_code')
ours['growth_new'] = (ours['nat_new'] - ours['base_nat_new']) / ours['base_nat_new']
ours['growth_old'] = (ours['nat_old'] - ours['base_nat_old']) / ours['base_nat_old']
ours['bartik'] = (ours['share_new'] * ours['growth_new'] +
                  (1-ours['share_new']) * ours['growth_old'])

# Match by LA name
ours['la_name_lower']  = ours['la_name'].str.strip().str.lower()
rama['la_name_lower']  = rama['local_auth'].str.strip().str.lower()

print('='*70)
print('PANEL COMPARISON: OURS vs RAMA')
print('='*70)

# Correlations in our panel
a = ours[ours['year']==2020]
print('\nOUR correlations (2020):')
print(f'  bartik vs tot:     {a[["bartik","tot"]].corr().iloc[0,1]:.3f}')
print(f'  bartik vs tot_new: {a[["bartik","tot_new"]].corr().iloc[0,1]:.3f}')

r2020 = rama[rama['year']==2020]
print(f"\nRAMA correlations (2020):")
print(f"  bartik vs retailers:     {r2020[['bartik_iv_2016','retailers']].corr().iloc[0,1]:.3f}")
print(f"  bartik vs retailers_new: {r2020[['bartik_iv_2016','retailers_new']].corr().iloc[0,1]:.3f}")

# Merge matched LAs
merged = ours[ours['year']==2020][
    ['la_name_lower','tot','tot_new','tot_old','bartik','share_new']
].merge(
    r2020[['la_name_lower','retailers','retailers_new',
           'retailers_old','bartik_iv_2016']],
    on='la_name_lower', how='inner'
)

print(f'\nMatched LAs: {len(merged)} of {len(a)} ours / {len(r2020)} Ramas')

print('\nRETAIL DIFFERENCES (ours - Ramas):')
merged['diff_tot'] = merged['tot'] - merged['retailers']
merged['diff_new'] = merged['tot_new'] - merged['retailers_new']
print(f'  Total:      mean={merged["diff_tot"].mean():.1f}, '
      f'std={merged["diff_tot"].std():.1f}')
print(f'  Discounters: mean={merged["diff_new"].mean():.1f}, '
      f'std={merged["diff_new"].std():.1f}')

print('\nBARTIK COMPARISON (2020):')
print(f'  Our bartik mean:   {merged["bartik"].mean():.4f}')
print(f'  Ramas bartik mean: {merged["bartik_iv_2016"].mean():.4f}')
print(f'  Correlation:       {merged[["bartik","bartik_iv_2016"]].corr().iloc[0,1]:.3f}')

print('\nLARGEST RETAIL DIFFERENCES:')
print(merged.nlargest(10,'diff_tot')[
    ['la_name_lower','tot','retailers','diff_tot',
     'tot_new','retailers_new','diff_new']
].to_string())

print('\nLAs with zero discounters in our panel but nonzero in Ramas:')
zero_ours = merged[(merged['tot_new']==0) & (merged['retailers_new']>0)]
print(zero_ours[['la_name_lower','tot_new','retailers_new']].to_string()
      if len(zero_ours) > 0 else '  None')

print('\nLAs with nonzero discounters in ours but zero in Ramas:')
zero_rama = merged[(merged['tot_new']>0) & (merged['retailers_new']==0)]
print(zero_rama[['la_name_lower','tot_new','retailers_new']].to_string()
      if len(zero_rama) > 0 else '  None')
