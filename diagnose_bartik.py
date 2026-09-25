"""
diagnose_bartik.py - Diagnose why first-stage F is weak.
"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/intermediate/england_panel_sfc.csv')
df = df.drop_duplicates(subset=['la_code','year'])
df = df[~df['la_code'].isin({'E09000001','E06000053'})]

# 2016 baseline
base = df[df['year']==2016][['la_code','la_name','tot_new','tot_old','tot']].copy()
base['share_new'] = base['tot_new'] / base['tot']

print('2016 DISCOUNT SHARE DISTRIBUTION')
print('='*50)
print(base['share_new'].describe().round(3).to_string())
print()
print(f'LAs with zero stores: {(base["tot"]==0).sum()}')
print(f'LAs with zero discount: {(base["tot_new"]==0).sum()}')
print()

# Check year-on-year retail growth (the other component of Bartik)
print('NATIONAL RETAIL TOTALS BY YEAR (discount chains)')
by_year = df.groupby('year')[['tot_new','tot_old','tot']].sum()
by_year['disc_growth'] = by_year['tot_new'] / by_year.loc[2016,'tot_new'] - 1
by_year['inc_growth']  = by_year['tot_old'] / by_year.loc[2016,'tot_old'] - 1
print(by_year[['tot_new','tot_old','disc_growth','inc_growth']].round(3).to_string())
print()

# Check Bartik variation
df2 = df.copy()
base2 = base[['la_code','share_new']].rename(columns={'share_new':'share_new_2016'})
df2 = df2.merge(base2, on='la_code')

nat = df2.groupby('year')[['tot_new','tot_old']].sum().reset_index()
nat.columns = ['year','nat_new','nat_old']
df2 = df2.merge(nat, on='year')
df2['nat_new_excl'] = df2['nat_new'] - df2['tot_new']
df2['nat_old_excl'] = df2['nat_old'] - df2['tot_old']

base_nat = df2[df2['year']==2016][['la_code','nat_new_excl','nat_old_excl']].rename(
    columns={'nat_new_excl':'base_nat_new','nat_old_excl':'base_nat_old'})
df2 = df2.merge(base_nat, on='la_code')
df2['growth_new'] = (df2['nat_new_excl'] - df2['base_nat_new']) / df2['base_nat_new']
df2['growth_old'] = (df2['nat_old_excl'] - df2['base_nat_old']) / df2['base_nat_old']
df2['bartik'] = df2['share_new_2016']*df2['growth_new'] + (1-df2['share_new_2016'])*df2['growth_old']

analysis = df2[df2['year'].between(2020,2023)]
print('BARTIK INSTRUMENT STATS (2020-2023)')
print(analysis['bartik'].describe().round(4).to_string())
print()
print(f'Correlation (bartik, tot): {analysis[["bartik","tot"]].corr().iloc[0,1]:.3f}')
print()

# Check if growth differential exists
print('GROWTH DIFFERENTIAL (2020-2023 vs 2016):')
for year in [2020,2021,2022,2023]:
    yr = df2[df2['year']==year].iloc[0]
    print(f'  {year}: discount growth={yr["growth_new"]:.3f}, incumbent growth={yr["growth_old"]:.3f}, diff={yr["growth_new"]-yr["growth_old"]:.3f}')
