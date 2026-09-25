"""
check_rama_pop.py - Check what population variable Rama uses.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

r = pd.read_stata('data/rama.dta')
r2020 = r[r['year']==2020].copy()

print('benefit_claimants stats 2020:')
print(r2020['benefit_claimants'].describe().round(1).to_string())
print()
print('pop_all stats 2020:')
print(r2020['pop_all'].describe().round(0).to_string())
print()
print('pop_60 stats 2020:')
print(r2020['pop_60'].describe().round(0).to_string())
print()

# What is pop_all? Total or working age?
# England working-age (16-64) is ~63% of total population
# If pop_all mean is ~374k and total LA pop is ~500k, it's working age
# If pop_all mean is ~374k and matches total LA pop, it's total

# Check ratio of pop_all to pop_60
r2020['pop_ratio'] = r2020['pop_all'] / r2020['pop_60']
print('pop_all / pop_60 ratio:')
print(r2020['pop_ratio'].describe().round(3).to_string())
print()

# Compute rates
r2020['rate_over_popall'] = r2020['benefit_claimants'] / r2020['pop_all'] * 1000
r2020['rate_over_pop60']  = r2020['benefit_claimants'] / r2020['pop_60']  * 1000

print('Claimant rate per 1000 pop_all:')
print(r2020['rate_over_popall'].describe().round(3).to_string())
print()
print('Claimant rate per 1000 pop_60:')
print(r2020['rate_over_pop60'].describe().round(3).to_string())
print()

# Check a few specific LAs
sample = r2020[['local_auth','benefit_claimants','pop_all','pop_60',
                'rate_over_popall','rate_over_pop60']].head(10)
print('Sample LAs:')
print(sample.to_string())
