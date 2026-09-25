"""
check_paper_consistency.py - Compare England SfC panel to Rama's paper Table 2.

Paper reference: Radakrishnan et al. "Retail Employment Expansion and the
Adult Social Care Workforce: Evidence from England's Local Labour Markets"

Table 2 benchmark values (150 English LAs, 2020-2023):

  Year  Retailers    Population   Pop 60+   Vacancies   Benefits   CQC
        Median(IQR)  Mean(SD)     Mean      Mean(SD)    Mean(SD)   Mean(SD)
  2020  32(23,52)    373.7(286)   89.4k     532(487)    10,800     63(50)
  2021  32(24,55)    375.9(288)   91.2k     774(637)    11,298     68(52)
  2022  33(24,56)    378.0(290)   93.1k     752(635)    8,009      74(57)
  2023  36(26,59)    379.9(291)   95.0k     612(532)    7,777      82(64)

Note on differences vs paper:
  - Paper uses 150 LAs; our panel has 153 (minor boundary handling difference)
  - Paper population in thousands (hundreds of thousands in data table)
  - Vacancies = vacant_posts from SfC (independent sector)
  - Benefits = claimants_mean (annual mean of monthly Experimental CC)
  - CQC Providers not in our panel yet (would need separate download)
  - Retailers = tot (total major retailers per LA)
  - Pop 60+ vs our Pop 65+ (paper uses 60+, we use 65+ - expect ~20% lower)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pandas as pd
import numpy as np

df = pd.read_csv('data/intermediate/england_panel_sfc.csv')

# Filter to 2020-2023, deduplicate to one row per LA-year
# (panel is long on measure for wellbeing)
panel = df[(df['year'] >= 2020) & (df['year'] <= 2023)].drop_duplicates(
    subset=['la_code', 'year']
).copy()

print("=" * 70)
print("CONSISTENCY CHECK: Panel vs Rama's Paper Table 2")
print("=" * 70)
print(f"Panel LAs: {panel['la_code'].nunique()} (paper: 150)")
print()

# Paper benchmark values
paper = {
    2020: {'retailers_med': 32, 'retailers_q1': 23, 'retailers_q3': 52,
           'pop_mean': 373700, 'pop_60_mean': 89400,
           'vacancies_mean': 532, 'benefits_mean': 10800, 'cqc_mean': 63},
    2021: {'retailers_med': 32, 'retailers_q1': 24, 'retailers_q3': 55,
           'pop_mean': 375900, 'pop_60_mean': 91200,
           'vacancies_mean': 774, 'benefits_mean': 11298, 'cqc_mean': 68},
    2022: {'retailers_med': 33, 'retailers_q1': 24, 'retailers_q3': 56,
           'pop_mean': 378000, 'pop_60_mean': 93100,
           'vacancies_mean': 752, 'benefits_mean': 8009, 'cqc_mean': 74},
    2023: {'retailers_med': 36, 'retailers_q1': 26, 'retailers_q3': 59,
           'pop_mean': 379900, 'pop_60_mean': 95000,
           'vacancies_mean': 612, 'benefits_mean': 7777, 'cqc_mean': 82},
}

print(f"{'Variable':<30} {'Year':<6} {'Our panel':>12} {'Paper':>12} {'Diff%':>8}")
print("-" * 70)

for year in [2020, 2021, 2022, 2023]:
    yr = panel[panel['year'] == year]
    p  = paper[year]

    # Retailers
    our_med = yr['tot'].median()
    our_q1  = yr['tot'].quantile(0.25)
    our_q3  = yr['tot'].quantile(0.75)
    diff = (our_med - p['retailers_med']) / p['retailers_med'] * 100
    print(f"{'Retailers (median)':30} {year:<6} {our_med:>12.1f} "
          f"{p['retailers_med']:>12.0f} {diff:>+7.1f}%")
    print(f"{'  IQR':30} {'':6} "
          f"({our_q1:.0f},{our_q3:.0f})    ({p['retailers_q1']},{p['retailers_q3']})")

    # Population (total)
    our_pop = yr['pop_total'].mean()
    diff = (our_pop - p['pop_mean']) / p['pop_mean'] * 100
    print(f"{'Population mean':30} {year:<6} {our_pop:>12,.0f} "
          f"{p['pop_mean']:>12,.0f} {diff:>+7.1f}%")

    # Population 65+ (we have 65+, paper has 60+)
    our_pop65 = yr['pop_65plus'].mean()
    print(f"{'Pop 65+ (our) / 60+ (paper)':30} {year:<6} {our_pop65:>12,.0f} "
          f"{p['pop_60_mean']:>12,.0f}  [60+ vs 65+]")

    # Vacancies (filled posts missing SfC suppression)
    our_vac = yr['vacant_posts'].mean()
    diff = (our_vac - p['vacancies_mean']) / p['vacancies_mean'] * 100
    n_obs = yr['vacant_posts'].notna().sum()
    print(f"{'Vacancies mean (n={n_obs})':30} {year:<6} {our_vac:>12.1f} "
          f"{p['vacancies_mean']:>12.0f} {diff:>+7.1f}%")

    # Benefits (claimant count)
    our_ben = yr['claimants_mean'].mean()
    diff = (our_ben - p['benefits_mean']) / p['benefits_mean'] * 100
    print(f"{'Claimants mean':30} {year:<6} {our_ben:>12.1f} "
          f"{p['benefits_mean']:>12.0f} {diff:>+7.1f}%")

    print()

print("=" * 70)
print("NOTES")
print("=" * 70)
print("1. Retailers: we count at upper-tier LA, paper at LA level — should match")
print("2. Population: minor differences expected (we use 2023 file, paper uses projections)")
print("3. Pop 65+ vs 60+: our figure will be ~20-25% lower than paper's")
print("4. Vacancies: paper has 150 LAs, we have 153; suppressed values affect mean")
print("5. Claimants: paper uses annual figure, we use annual mean of monthly data")
print("6. CQC Providers: not in our panel (would need separate Skills for Care download)")

print()
print("YEAR-ON-YEAR TRENDS (direction should match paper):")
for var, col, label in [
    ('Retailers', 'tot', 'median'),
    ('Vacancies', 'vacant_posts', 'mean'),
    ('Claimants', 'claimants_mean', 'mean'),
]:
    vals = []
    for year in [2020, 2021, 2022, 2023]:
        yr = panel[panel['year'] == year]
        if label == 'median':
            vals.append(yr[col].median())
        else:
            vals.append(yr[col].mean())
    trend = ' -> '.join([f'{v:.0f}' for v in vals])
    print(f"  {var:<15}: {trend}")
