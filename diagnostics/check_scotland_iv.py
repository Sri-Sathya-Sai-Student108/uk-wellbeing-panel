#!/usr/bin/env python3
"""
check_scotland_iv.py - Main IV analysis on the assembled Scotland panel.

Runs the Scotland-equivalent of bartik_check.py's Section 3: does
retail expansion affect social care vacancy_rate and benefit claims
(Dec + annual), using the validated 29-council specification (3 island
authorities excluded -- see check_scotland_bartik.py and README.SCOT).

Reuses construct_bartik(), first_stage(), and run_iv() from
bartik_check.py UNCHANGED. Feeding them the 29-council Scotland panel
automatically gives the Scotland-only leave-one-out pool, same as
check_scotland_bartik.py.

Analysis window: 2020-2023, same as England's YEAR_MIN_ANALYSIS/
YEAR_MAX_ANALYSIS -- this happens to line up exactly with the years
Scotland's SSSC vacancy_rate is available for, so no window mismatch
between the two outcomes.

vacancy_rate scale note: SSSC's source figure is a decimal (e.g. 0.083
for 8.3%). Converted to the same 0-100 percentage-point scale as
England's constructed vacancy_rate here, at load time, so the two
nations' vacancy_rate coefficients are on comparable units.

Usage:
  python check_scotland_iv.py
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bartik_check import construct_bartik, first_stage, run_iv
from config import DATA_DIR

PANEL_FILE = os.path.join(DATA_DIR, 'intermediate', 'scotland_panel.csv')

YEAR_MIN_ANALYSIS = 2020
YEAR_MAX_ANALYSIS = 2023

# Same structural exclusion as check_scotland_bartik.py -- remote
# island authorities, decided on geography, not on growth performance.
SCOTLAND_ISLAND_CODES = {
    'S12000023',  # Orkney Islands
    'S12000027',  # Shetland Islands
    'S12000013',  # Na h-Eileanan Siar (Western Isles)
}


def load_scotland_panel():
    print("\nLoading Scotland panel...")
    df = pd.read_csv(PANEL_FILE)
    print(f"  Loaded: {df['la_code'].nunique()} councils, "
          f"years {df['year'].min()}-{df['year'].max()}, {len(df)} rows")

    n_before = df['la_code'].nunique()
    df = df[~df['la_code'].isin(SCOTLAND_ISLAND_CODES)].copy()
    n_after = df['la_code'].nunique()
    print(f"  Excluding {n_before - n_after} island authorities "
          f"(Orkney, Shetland, Na h-Eileanan Siar): "
          f"{n_after} councils remain")

    # Convert SSSC vacancy_rate from decimal (0.083) to percentage-point
    # scale (8.3), matching England's constructed vacancy_rate units.
    df['vacancy_rate'] = df['vacancy_rate'] * 100

    # Benefit rate, same construction as England's load_data()
    df['benefit_rate'] = df['claimants_december'] / df['pop_total'] * 1000
    df['benefit_rate_annual'] = df['claimants_annual'] / df['pop_total'] * 1000

    return df


def main():
    df = load_scotland_panel()

    df = construct_bartik(df)
    f_stat, fs_coef = first_stage(df)

    print(f"\n{'=' * 70}")
    print("MAIN IV ANALYSIS (2020-2023) -- SCOTLAND, 29 COUNCILS")
    print(f"{'=' * 70}")

    analysis = df[df['year'].between(YEAR_MIN_ANALYSIS,
                                      YEAR_MAX_ANALYSIS)].copy()
    controls = ['pop_total', 'pop_65plus']

    outcomes = [
        ('vacancy_rate',        'Vacancy rate',
         'Scope: ALL social services, not adult-only (see README.SCOT)'),
        ('benefit_rate',        'Benefit rate (Dec)',
         'England benchmark: -1.057, p=0.001'),
        ('benefit_rate_annual', 'Benefit rate (annual)',
         'England benchmark: +0.632, p<0.001'),
    ]

    print()
    print(f"  {'Outcome':<22} {'Coef':>10} {'SE':>8} {'p':>8} "
          f"{'F-stat':>8}  {'Note'}")
    print("  " + "-" * 100)

    for outcome, label, note in outcomes:
        r = run_iv(analysis, outcome, 'tot', 'bartik', controls,
                   'la_code', 'year', label)
        if r is None:
            print(f"  {label:<22} could not estimate (insufficient data)")
            continue
        sig = '***' if r.pval < 0.01 else '**' if r.pval < 0.05 \
            else '*' if r.pval < 0.10 else ''
        print(f"  {label:<22} {r.coef:>10.3f} {r.se:>8.3f} "
              f"{r.pval:>8.3f} {r.first_stage_f:>8.2f}  {note} {sig}")

    print()
    print(f"{'=' * 70}")
    print("NOTES")
    print(f"{'=' * 70}")
    print("  - First-stage F above is from the 2020-2023 analysis window")
    print("    specifically (may differ slightly from the 26.63 full-2016-")
    print("    2023-window figure in check_scotland_bartik.py).")
    print("  - vacancy_rate covers ALL social services (children, young")
    print("    people, adults, older people) -- not adult-only like")
    print("    England's Skills for Care data. See README.SCOT Section 1.")
    print("  - N=29 councils -- smaller than England's 148, treat")
    print("    significance thresholds accordingly.")


if __name__ == '__main__':
    main()
