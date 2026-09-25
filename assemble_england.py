#!/usr/bin/env python3
"""
assemble_england.py - Assemble the base England panel.

Joins claimants, population, PAYE overseas share, and wellbeing
at lower-tier LA level. Retail and Skills for Care are joined
separately at upper-tier geography (see assemble_england_sfc.py).

Dependencies (run first):
  python make.py panel-data     # claimants + population
  python make.py paye           # overseas share
  python make.py curated        # wellbeing harmonised panel

Output:
  data/intermediate/england_panel_base.csv

Usage:
  python assemble_england.py
  python assemble_england.py --force
  python make.py england-panel
"""

import os, sys, warnings
import pandas as pd
import numpy as np
warnings.filterwarnings('ignore')

from config import DATA_DIR

INTERMEDIATE = os.path.join(DATA_DIR, 'intermediate')
CURATED      = os.path.join(DATA_DIR, 'curated')
OUTPUT_FILE  = os.path.join(INTERMEDIATE, 'england_panel_base.csv')

CC_FILE      = os.path.join(INTERMEDIATE, 'claimant_count_annual.csv')
POP_FILE     = os.path.join(INTERMEDIATE, 'population_annual.csv')
PAYE_FILE    = os.path.join(INTERMEDIATE, 'paye_overseas_la.csv')
WB_FILE      = os.path.join(CURATED,      'wellbeing_harmonised_panel.csv')

YEAR_MIN = 2016
YEAR_MAX = 2023


def check_inputs():
    required = {
        'Claimant count':    CC_FILE,
        'Population':        POP_FILE,
        'PAYE overseas':     PAYE_FILE,
        'Wellbeing panel':   WB_FILE,
    }
    missing = {k: v for k, v in required.items() if not os.path.exists(v)}
    if missing:
        print("\nERROR: Missing input files:")
        for name, path in missing.items():
            print(f"  {name}: {path}")
        print("\nRun:")
        print("  python make.py panel-data")
        print("  python make.py paye")
        print("  python make.py curated")
        return False
    return True


def assemble_england_panel(force_refresh=False):
    os.makedirs(INTERMEDIATE, exist_ok=True)

    if os.path.exists(OUTPUT_FILE) and not force_refresh:
        print(f"  Loading cached England base panel from {OUTPUT_FILE}...")
        df = pd.read_csv(OUTPUT_FILE)
        print(f"  {len(df):,} obs, {df['la_code'].nunique()} LAs, "
              f"years {df['year'].min()}-{df['year'].max()}")
        return df

    if not check_inputs():
        return None

    print("\n1. Loading inputs...")
    cc   = pd.read_csv(CC_FILE)
    pop  = pd.read_csv(POP_FILE)
    paye = pd.read_csv(PAYE_FILE)
    wb   = pd.read_csv(WB_FILE)

    # Filter to England, study period
    for name, df in [('cc', cc), ('pop', pop), ('paye', paye)]:
        pass

    cc   = cc[(cc['la_code'].str.startswith('E', na=False)) &
              (cc['year'] >= YEAR_MIN) & (cc['year'] <= YEAR_MAX)].copy()
    pop  = pop[(pop['la_code'].str.startswith('E', na=False)) &
               (pop['year'] >= YEAR_MIN) & (pop['year'] <= YEAR_MAX)].copy()
    paye = paye[(paye['la_code'].str.startswith('E', na=False)) &
                (paye['year'] >= YEAR_MIN) & (paye['year'] <= YEAR_MAX)].copy()
    wb   = wb[(wb['la_code'].str.startswith('E', na=False)) &
              (wb['year'] >= YEAR_MIN) & (wb['year'] <= YEAR_MAX)].copy()

    print(f"  Claimants:  {cc['la_code'].nunique()} English LAs, "
          f"years {cc['year'].min()}-{cc['year'].max()}")
    print(f"  Population: {pop['la_code'].nunique()} English LAs")
    print(f"  PAYE:       {paye['la_code'].nunique()} English LAs")
    print(f"  Wellbeing:  {wb['la_code'].nunique()} English LAs, "
          f"years {wb['year'].min()}-{wb['year'].max()}")

    print("\n2. Assembling panel...")

    # Start from claimants as the spine (most complete LA coverage)
    # NOTE: carries BOTH claimants_december (matches Radakrishnan et al. 2025)
    # and claimants_annual (annual mean, for the seasonal-vs-permanent story)
    panel = cc[['la_code', 'la_name', 'year',
                'claimants_december', 'claimants_annual']].copy()

    # Population
    panel = panel.merge(
        pop[['la_code', 'year', 'pop_total', 'pop_65plus']],
        on=['la_code', 'year'], how='left'
    )

    # PAYE overseas share
    panel = panel.merge(
        paye[['la_code', 'year', 'region', 'overseas_share']],
        on=['la_code', 'year'], how='left'
    )

    # Wellbeing — long format, keep as-is
    panel = panel.merge(
        wb[['la_code', 'year', 'measure', 'value', 'se',
            'ci_lower', 'ci_upper']],
        on=['la_code', 'year'], how='left'
    )

    panel['nation'] = 'England'

    # Column order
    cols = ['la_code', 'la_name', 'year', 'nation', 'region',
            'claimants_december', 'claimants_annual', 'pop_total', 'pop_65plus', 'overseas_share',
            'measure', 'value', 'se', 'ci_lower', 'ci_upper']
    panel = panel[[c for c in cols if c in panel.columns]]
    panel = panel.sort_values(['la_code', 'year', 'measure']).reset_index(drop=True)

    print("\n" + "=" * 60)
    print("ENGLAND BASE PANEL SUMMARY")
    print("=" * 60)
    print(f"  LAs:          {panel['la_code'].nunique()}")
    print(f"  Years:        {sorted(panel['year'].unique())}")
    print(f"  Measures:     {sorted(panel['measure'].dropna().unique())}")
    print(f"  Observations: {len(panel)}")
    print(f"\n  Missing values:")
    for col in ['claimants_december', 'claimants_annual', 'pop_total', 'overseas_share',
                'region', 'value']:
        n   = panel[col].isna().sum()
        pct = n / len(panel) * 100
        print(f"    {col:<20} {n:>6} ({pct:5.1f}%)")

    panel.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Saved: {OUTPUT_FILE}")
    return panel


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print("ENGLAND BASE PANEL ASSEMBLER")
    print("=" * 60)
    assemble_england_panel(force_refresh=args.force)
