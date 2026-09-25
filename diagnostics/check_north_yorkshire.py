"""
check_north_yorkshire.py - Check North Yorkshire and county coverage.
"""
import pandas as pd

sfc = pd.read_csv('data/intermediate/england_panel_sfc.csv')
rama = pd.read_stata('data/rama.dta')
lad_cty = pd.read_csv('data/lad_to_county.csv')

sfc_w = sfc.drop_duplicates(subset=['la_code','year'])
rama_w = rama.drop_duplicates(subset=['local_auth'])

# Check E10 counties in our panel vs Rama
sfc_e10 = sfc_w[sfc_w['la_code'].str.startswith('E10')][
    ['la_code','la_name']].drop_duplicates()
print(f'E10 counties in our SfC panel: {len(sfc_e10)}')
print(sfc_e10.sort_values('la_name').to_string())
print()

# Check what Rama has for Yorkshire
print('Rama entries containing Yorkshire:')
york = rama_w[rama_w['local_auth'].str.contains('Yorkshire', case=False, na=False)]
print(york['local_auth'].to_string())
print()

# Check Adur specifically
print('Adur in our panel:')
adur = sfc_w[sfc_w['la_name'].str.contains('Adur', case=False, na=False)]
print(adur[['la_code','la_name']].drop_duplicates().to_string())
print()

# Names in our panel but not Rama
sfc_names = set(sfc_w['la_name'].str.strip().str.lower().unique())
rama_names = set(rama_w['local_auth'].str.strip().str.lower().unique())
print('In our panel but not Ramas (first 30):')
diff = sorted(sfc_names - rama_names)
for n in diff[:30]:
    code = sfc_w[sfc_w['la_name'].str.lower()==n]['la_code'].iloc[0]
    print(f'  {code}  {n}')
print()
print('In Ramas but not our panel:')
for n in sorted(rama_names - sfc_names)[:20]:
    print(f'  {n}')
