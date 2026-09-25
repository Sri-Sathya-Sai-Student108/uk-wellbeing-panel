#!/usr/bin/env python3
"""
check_scotland_bartik.py - Scotland-only Bartik first-stage diagnostic.

Tests whether a Scotland-only leave-one-out Bartik instrument (32 councils
as their own closed system, per Peter's decision -- Option A, not pooled
with England) has any real first-stage power, BEFORE building out the
full scotland_panel.py assembly.

Reuses construct_bartik() and first_stage() from bartik_check.py
UNCHANGED -- both are generic (only need la_code/year/tot/tot_new/tot_old,
plus pop_total/pop_65plus for first_stage), so feeding them Scotland-only
data automatically gives a Scotland-only leave-one-out pool with zero
code changes. This is deliberate: it means whatever comes out of this
diagnostic is directly comparable to England's Section 1/2 output
(same construction, same first-stage regression), not a bespoke
Scotland-specific method that could itself be a source of difference.

Context: 2016 baseline discount-share summary already showed Scotland's
cross-sectional spread is much narrower than England's (mean 0.128 vs
0.161, max 0.207 vs 0.370, std 0.054) -- a structural reason to expect
a weaker Scotland-only instrument, separate from anything about sample
size. This script checks whether that translates into a weak first
stage in practice, rather than just inferring it from the baseline
share summary alone.

Known limitations carried in from earlier discussion (documented here,
not fixed):
  - Co-op correctly counted as an incumbent for Scotland already, in
    retail_panel.py's INCUMBENTS_SCOTLAND set (not a concern for tot
    completeness)
  - No geographic density control included in the first stage,
    deliberately -- retail clustering could be a "bad control" (itself
    a consequence of the expansion process being instrumented), so
    it's left out of the causal specification entirely
  - Window fixed at 2016-2023, per the decision to publish on the
    original window first and handle any extension in a separate
    thread

Usage:
  python check_scotland_bartik.py
"""

import os
import sys
import warnings

import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

# Allow running from diagnostics/ subfolder, same convention as
# bartik_check.py and the other check_*.py scripts in this project.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bartik_check import construct_bartik, first_stage
from config import DATA_DIR

RETAIL_SCOTLAND_FILE = os.path.join(DATA_DIR, 'intermediate',
                                     'retail_data_scotland.csv')
POP_FILE = os.path.join(DATA_DIR, 'intermediate', 'population_annual.csv')

YEAR_MIN_ANALYSIS = 2020
YEAR_MAX_ANALYSIS = 2023

# Remote island council areas -- excluded on the SAME kind of grounds as
# England's City of London / Isles of Scilly exclusion: a pre-determined
# structural characteristic (remote archipelago geography, populations in
# the low 20-thousands), decided independently of how they happen to
# perform on the Bartik growth measure. NOT selected because they show
# weak growth -- that would be selecting on the outcome and would
# invalidate the exercise, not fix it.
SCOTLAND_ISLAND_CODES = {
    'S12000023',  # Orkney Islands
    'S12000027',  # Shetland Islands
    'S12000013',  # Na h-Eileanan Siar (Western Isles)
}


def load_scotland_data():
    """
    Load Scotland retail data and merge in population (S-codes only).
    Deliberately does NOT touch England's data at all -- this keeps the
    Scotland-only leave-one-out pool completely separate, per Option A.
    """
    print("\nLoading Scotland data...")

    retail = pd.read_csv(RETAIL_SCOTLAND_FILE)
    print(f"  Retail: {retail['la_code'].nunique()} councils, "
          f"years {retail['year'].min()}-{retail['year'].max()}")

    pop = pd.read_csv(POP_FILE)
    pop = pop[pop['la_code'].str.startswith('S', na=False)].copy()
    print(f"  Population: {pop['la_code'].nunique()} councils")

    # NOTE: exact population column names not yet confirmed -- if this
    # merge fails or pop_total/pop_65plus aren't found, check
    # population_annual.csv's actual columns before assuming they match
    # England's naming.
    needed_pop_cols = ['la_code', 'year', 'pop_total', 'pop_65plus']
    missing = [c for c in needed_pop_cols if c not in pop.columns]
    if missing:
        print(f"  WARNING: population_annual.csv missing expected columns "
              f"{missing}. Actual columns: {pop.columns.tolist()}")
        print("  Cannot proceed with first-stage diagnostic (needs "
              "pop_total, pop_65plus as controls) until this is resolved.")
        return None

    df = retail.merge(pop[needed_pop_cols], on=['la_code', 'year'],
                       how='left')

    n_missing_pop = df['pop_total'].isna().sum()
    if n_missing_pop > 0:
        print(f"  WARNING: {n_missing_pop} rows have no population match "
              f"-- check la_code alignment between retail and population "
              f"files before trusting the diagnostic below.")

    return df


def run_diagnostic(df, label):
    """Run construct_bartik() + first_stage() on a given Scotland panel
    and return the F-stat, with a labeled header."""
    print(f"\n{'#' * 70}")
    print(f"# {label}")
    print(f"{'#' * 70}")
    df = construct_bartik(df.copy())
    f_stat, fs_coef = first_stage(df)
    return f_stat


def main():
    df = load_scotland_data()
    if df is None:
        return

    print(f"\n  Scotland panel: {df['la_code'].nunique()} councils, "
          f"{df['year'].min()}-{df['year'].max()}, "
          f"{len(df)} council-year rows")

    # Run 1: all 32 councils (baseline, already seen: F=7.52)
    f_all = run_diagnostic(df, "ALL 32 COUNCILS")

    # Run 2: island authorities excluded BEFORE construct_bartik() runs --
    # this removes them from the leave-one-out national pool too, not
    # just from the final regression sample, mirroring exactly how
    # England drops City of London/Scilly before construct_bartik().
    df_no_islands = df[~df['la_code'].isin(SCOTLAND_ISLAND_CODES)].copy()
    n_excluded = df['la_code'].nunique() - df_no_islands['la_code'].nunique()
    print(f"\n  Excluding {n_excluded} island authorities: "
          f"{sorted(SCOTLAND_ISLAND_CODES & set(df['la_code'].unique()))}")
    f_no_islands = run_diagnostic(df_no_islands,
                                   "ISLAND AUTHORITIES EXCLUDED (29 councils)")

    print(f"\n{'=' * 70}")
    print("SCOTLAND vs ENGLAND FIRST-STAGE COMPARISON")
    print(f"{'=' * 70}")
    print(f"  Scotland, all 32 councils:        F = {f_all:.2f}")
    print(f"  Scotland, islands excluded (29):  F = {f_no_islands:.2f}")
    print(f"  England, 148 LAs (for reference): F = 30.84")
    print(f"  Stock-Yogo 10% threshold: 16.38")
    print()
    print("  If excluding islands moves F substantially, that supports")
    print("  treating them the same way as City of London/Scilly in")
    print("  England -- structurally non-comparable units, decided on")
    print("  what they are (remote archipelago geography), not on how")
    print("  they performed in the growth data.")


if __name__ == '__main__':
    main()
