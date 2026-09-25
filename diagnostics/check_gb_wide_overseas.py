#!/usr/bin/env python3
"""
check_gb_wide_overseas.py - Does adding Scotland (as a low-overseas
unit) to the regional panel move the retail-effect coefficients when
split by high/low overseas access?

Builds a FRESH 10-unit panel (9 English regions + Scotland as one
combined unit) with a genuine GB-WIDE leave-one-out Bartik instrument
-- NOT a shortcut of appending Scotland's already-computed 29-council
value, which was built with a separate Scotland-only leave-one-out pool
and isn't on the same footing as England's regions' instrument. Every
unit here is computed the same way, against the same GB-wide pool.

With Scotland added, the median overseas-share split becomes a clean
5-5 (previously an unbalanced 4-5 among England's 9 regions alone):
  LOW:  North East, Scotland, Yorkshire & Humber, North West, South West
  HIGH: East Midlands, West Midlands, East of England, South East, London

Explicitly exploratory/fingerprint-level, per the framing used
throughout today's Scotland work -- not a rigorous causal estimate.
G=5 per group is a very small cluster count; treat results as scoping
signals, not findings.

Scotland's vacancy_rate here uses SSSC's own published national
"Grand total" rate (matching how England's regions are genuine
national-region rates), not a re-aggregation from LA-level rates --
avoids introducing a weighting question the source data doesn't
support answering precisely (see README.SCOT Section 1 on why raw WTE
counts aren't published at LA level).

NOT TESTED END-TO-END -- the underlying raw files (England's LA panel,
Scotland's retail/claimants/population/PAYE files) aren't available in
this environment. Run and report back before trusting the numbers.

Usage:
  python check_gb_wide_overseas.py
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bartik_check import load_data, load_paye_regional, run_iv
from config import DATA_DIR

YEAR_MIN_ANALYSIS = 2020
YEAR_MAX_ANALYSIS = 2023

RETAIL_SCOTLAND_FILE = os.path.join(DATA_DIR, 'intermediate', 'retail_data_scotland.csv')
CLAIMANTS_FILE = os.path.join(DATA_DIR, 'intermediate', 'claimant_count_annual.csv')
POP_FILE = os.path.join(DATA_DIR, 'intermediate', 'population_annual.csv')

SCOTLAND_ISLAND_CODES = {'S12000023', 'S12000027', 'S12000013'}

# SSSC "Grand total" vacancy_rate (all 32 councils, matching SSSC's own
# national scope -- NOT the 29-council subset used for instrument
# validation). Verified directly from each file's own Grand total row
# (not transcribed from memory): 2020/2021/2022 cross-checked across
# the 2022 PDF, 2023 file, and 2024 file (all match exactly); 2023
# cross-checked between the 2023 and 2024 files (match exactly).
SCOTLAND_VACANCY_RATE_NATIONAL = {
    2020: 0.051, 2021: 0.081, 2022: 0.087, 2023: 0.075,
}


def build_england_regional():
    """England's 9 regions, SUMMED retail/outcome collapse -- same
    pattern as bartik_check.py's regional_mechanism(), reused here."""
    df = load_data()
    eng = df[~df['region'].isin(['Scotland', 'Wales', 'Northern Ireland'])].copy()

    retail_r = eng.groupby(['region', 'year']).agg(
        tot_new=('tot_new', 'sum'), tot_old=('tot_old', 'sum'),
        tot=('tot', 'sum'),
    ).reset_index()

    outcomes_r = eng[eng['year'].between(YEAR_MIN_ANALYSIS, YEAR_MAX_ANALYSIS)] \
        .groupby(['region', 'year']).agg(
            pop_total=('pop_total', 'sum'),
            vacant_posts=('vacant_posts', 'sum'),
            filled_posts=('filled_posts', 'sum'),
            claimants_december=('claimants_december', 'sum'),
            claimants_annual=('claimants_annual', 'sum'),
        ).reset_index()

    regional = retail_r.merge(outcomes_r, on=['region', 'year'], how='left')

    posts = regional['filled_posts'].fillna(0) + regional['vacant_posts'].fillna(0)
    regional['vacancy_rate'] = np.where(posts > 0,
                                        regional['vacant_posts'] / posts * 100, np.nan)
    regional['benefit_rate'] = regional['claimants_december'] / regional['pop_total'] * 1000
    regional['benefit_rate_annual'] = regional['claimants_annual'] / regional['pop_total'] * 1000

    return regional[['region', 'year', 'tot', 'tot_new', 'tot_old',
                      'vacancy_rate', 'benefit_rate', 'benefit_rate_annual']]


def build_scotland_national():
    """Scotland as ONE combined unit -- all 32 councils summed for
    retail/claimants/population, SSSC's own published national
    vacancy_rate (not re-aggregated from LA-level rates)."""
    retail = pd.read_csv(RETAIL_SCOTLAND_FILE)
    retail_nat = retail.groupby('year').agg(
        tot_new=('tot_new', 'sum'), tot_old=('tot_old', 'sum'),
        tot=('tot', 'sum'),
    ).reset_index()

    claimants = pd.read_csv(CLAIMANTS_FILE)
    claimants = claimants[claimants['la_code'].str.startswith('S', na=False)]
    claimants_nat = claimants.groupby('year').agg(
        claimants_december=('claimants_december', 'sum'),
        claimants_annual=('claimants_annual', 'sum'),
    ).reset_index()

    pop = pd.read_csv(POP_FILE)
    pop = pop[pop['la_code'].str.startswith('S', na=False)]
    pop_nat = pop.groupby('year')['pop_total'].sum().reset_index()

    scot = retail_nat.merge(claimants_nat, on='year', how='left') \
                      .merge(pop_nat, on='year', how='left')
    scot['region'] = 'Scotland'

    scot['vacancy_rate'] = scot['year'].map(SCOTLAND_VACANCY_RATE_NATIONAL)
    scot['vacancy_rate'] = scot['vacancy_rate'] * 100  # match England's 0-100 scale
    scot['benefit_rate'] = scot['claimants_december'] / scot['pop_total'] * 1000
    scot['benefit_rate_annual'] = scot['claimants_annual'] / scot['pop_total'] * 1000

    return scot[['region', 'year', 'tot', 'tot_new', 'tot_old',
                 'vacancy_rate', 'benefit_rate', 'benefit_rate_annual']]


def build_gb_bartik(panel):
    """Genuine GB-wide leave-one-out Bartik across all 10 units --
    every unit computed the same way against the same shared pool."""
    base = panel[panel['year'] == 2016][['region', 'tot_new', 'tot_old', 'tot']] \
        .rename(columns={'tot_new': 'base_new', 'tot_old': 'base_old', 'tot': 'base_tot'})
    base['share_new_2016'] = base['base_new'] / base['base_tot']
    base['share_old_2016'] = base['base_old'] / base['base_tot']
    panel = panel.merge(base[['region', 'share_new_2016', 'share_old_2016']],
                         on='region', how='left')

    gb = panel.groupby('year')[['tot_new', 'tot_old']].sum().reset_index() \
        .rename(columns={'tot_new': 'gb_new', 'tot_old': 'gb_old'})
    panel = panel.merge(gb, on='year')
    panel['gb_new_excl'] = panel['gb_new'] - panel['tot_new']
    panel['gb_old_excl'] = panel['gb_old'] - panel['tot_old']

    base_gb = panel[panel['year'] == 2016][['region', 'gb_new_excl', 'gb_old_excl']] \
        .rename(columns={'gb_new_excl': 'base_gb_new', 'gb_old_excl': 'base_gb_old'})
    panel = panel.merge(base_gb, on='region', how='left')

    panel['growth_new'] = (panel['gb_new_excl'] - panel['base_gb_new']) / panel['base_gb_new']
    panel['growth_old'] = (panel['gb_old_excl'] - panel['base_gb_old']) / panel['base_gb_old']
    panel['bartik_gb'] = (panel['share_new_2016'] * panel['growth_new'] +
                           panel['share_old_2016'] * panel['growth_old'])

    return panel


def get_overseas_share():
    """Overseas share by region, England + Scotland, 2016-2023 average
    -- used only to classify high/low, not as a regression variable."""
    paye = load_paye_regional()
    avg = paye.groupby('region')['overseas_share'].mean()
    return avg


def run_iv_simple(data, outcome):
    """Minimal single-instrument IV: outcome ~ tot_hat + year dummies,
    no entity FE (too few units per group for that), clustered by
    region. Same structure as run_iv_regional_simple() used for
    Scotland earlier today, generalized here."""
    needed = [outcome, 'tot', 'bartik_gb', 'region', 'year']
    est = data.dropna(subset=needed).copy()
    if len(est) < 6:
        return None

    yr_dummies = pd.get_dummies(est['year'], prefix='yr', drop_first=True).astype(float)
    yr_cols = yr_dummies.columns.tolist()
    for c in yr_cols:
        est[c] = yr_dummies[c].values

    clusters = est['region'].values
    unique_c = np.unique(clusters)
    G = len(unique_c)
    n = len(est)

    Z = np.column_stack([est['bartik_gb'].values] +
                         [est[c].values for c in yr_cols] + [np.ones(n)])
    y_fs = est['tot'].values.astype(float)
    b_fs, _, _, _ = np.linalg.lstsq(Z, y_fs, rcond=None)
    tot_hat = Z @ b_fs
    res_fs = y_fs - tot_hat
    k_fs = Z.shape[1]
    meat_fs = np.zeros((k_fs, k_fs))
    for c in unique_c:
        m = clusters == c
        s = Z[m].T @ res_fs[m]
        meat_fs += np.outer(s, s)
    try:
        ZtZ_inv = np.linalg.inv(Z.T @ Z)
        V_fs = (G/max(G-1,1)) * ((n-1)/max(n-k_fs,1)) * ZtZ_inv @ meat_fs @ ZtZ_inv
        f_stat = (b_fs[0] / np.sqrt(V_fs[0, 0])) ** 2
    except np.linalg.LinAlgError:
        return None

    y = est[outcome].values.astype(float)
    C = np.column_stack([est[c].values for c in yr_cols] + [np.ones(n)])
    X_ss = np.column_stack([tot_hat.reshape(-1, 1), C])
    k = X_ss.shape[1]
    try:
        b_ss, _, _, _ = np.linalg.lstsq(X_ss, y, rcond=None)
        resid = y - X_ss @ b_ss
        meat = np.zeros((k, k))
        for c in unique_c:
            m = clusters == c
            s = X_ss[m].T @ resid[m]
            meat += np.outer(s, s)
        XtX_inv = np.linalg.inv(X_ss.T @ X_ss)
        V = (G/max(G-1,1)) * ((n-1)/max(n-k,1)) * XtX_inv @ meat @ XtX_inv
        se = np.sqrt(V[0, 0])
        coef = b_ss[0]
        t = coef / se
        pval = 2 * (1 - stats.t.cdf(abs(t), df=max(G-1, 1)))
    except np.linalg.LinAlgError:
        return None

    return dict(coef=coef, se=se, pval=pval, f_stat=f_stat, n=n, G=G)


def main():
    print("Building England regional collapse...")
    eng_regional = build_england_regional()

    print("Building Scotland national collapse...")
    scot_regional = build_scotland_national()

    panel = pd.concat([eng_regional, scot_regional], ignore_index=True)
    print(f"\nCombined panel: {panel['region'].nunique()} units "
          f"(should be 10), years {panel['year'].min()}-{panel['year'].max()}")

    panel = build_gb_bartik(panel)

    overseas = get_overseas_share()
    median_share = overseas.median()
    high_regions = overseas[overseas > median_share].index.tolist()
    panel['high_overseas'] = panel['region'].isin(high_regions).astype(int)

    print(f"\nHigh/low overseas split (median={median_share:.3f}):")
    print(f"  LOW:  {sorted(overseas[overseas <= median_share].index.tolist())}")
    print(f"  HIGH: {sorted(high_regions)}")

    analysis = panel[panel['year'].between(YEAR_MIN_ANALYSIS, YEAR_MAX_ANALYSIS)].copy()

    outcomes = [
        ('vacancy_rate', 'Vacancy rate'),
        ('benefit_rate', 'Benefit rate (Dec)'),
        ('benefit_rate_annual', 'Benefit rate (annual)'),
    ]

    print(f"\n{'=' * 70}")
    print("10-UNIT GB-WIDE SPLIT: LOW vs HIGH OVERSEAS (WITH SCOTLAND)")
    print(f"{'=' * 70}")

    for outcome, label in outcomes:
        print(f"\n  {label}:")
        for grp, grp_label in [(0, 'LOW (incl. Scotland)'), (1, 'HIGH')]:
            sub = analysis[analysis['high_overseas'] == grp]
            r = run_iv_simple(sub, outcome)
            if r is None:
                print(f"    {grp_label:<22} could not estimate")
                continue
            sig = '***' if r['pval'] < 0.01 else '**' if r['pval'] < 0.05 \
                else '*' if r['pval'] < 0.10 else '(ns)'
            print(f"    {grp_label:<22} beta={r['coef']:>10.3f} "
                  f"(SE={r['se']:.3f}, p={r['pval']:.3f}) {sig}  "
                  f"F={r['f_stat']:.2f}  N={r['n']}, G={r['G']}")

    print(f"\n{'=' * 70}")
    print("COMPARISON: 9-REGION ENGLAND-ONLY RESULTS (no split, no Scotland)")
    print(f"{'=' * 70}")
    print("  Vacancy rate:          England benchmark not directly comparable")
    print("                         (this script's England collapse may differ")
    print("                         slightly from bartik_check.py Section 4)")
    print("  Benefit rate (Dec):    -")
    print("  Benefit rate (annual): -")
    print()
    print("  NOTE: G=5 per group -- extremely small cluster count. Treat as")
    print("  a scoping signal only. NOT tested end-to-end -- verify these")
    print("  numbers run cleanly before drawing any conclusion from them.")


if __name__ == '__main__':
    main()
