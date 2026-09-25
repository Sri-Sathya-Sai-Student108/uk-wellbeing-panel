#!/usr/bin/env python3
"""
check_scotland_overseas.py - Does Scotland look like a typical English
region on overseas worker share in health & social care, or does it
stand out?

Purely descriptive -- not a regression, not causal. Scotland sits in
the PAYE regional dataset as its own single region (confirmed earlier:
load_paye_regional() already keeps region_code starting with 'E12' or
'S'). This just asks: where does Scotland's overseas_share fall
relative to the 9 English regions' distribution -- is it a typical
region, or an outlier? Framed as a scoping "fingerprint" for possible
future research, not a finding to build causal claims on.

Usage:
  python check_scotland_overseas.py
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bartik_check import load_paye_regional


def main():
    paye = load_paye_regional()

    eng = paye[paye['region_code'].str.startswith('E12')].copy()
    scot = paye[paye['region_code'].str.startswith('S')].copy()

    print(f"\nEngland: {eng['region'].nunique()} regions, "
          f"years {eng['year'].min()}-{eng['year'].max()}")
    print(f"Scotland: {scot['region'].nunique()} region "
          f"(should be 1 -- Scotland is a single PAYE region, not "
          f"broken into sub-regions)")

    if scot['region'].nunique() != 1:
        print(f"  WARNING: expected exactly 1 Scotland region, found "
              f"{scot['region'].nunique()}: {scot['region'].unique()}")

    print(f"\n{'=' * 70}")
    print("OVERSEAS SHARE BY YEAR: SCOTLAND vs ENGLISH REGION RANGE")
    print(f"{'=' * 70}")
    print(f"  {'Year':<6} {'Scotland':>10} {'Eng min':>9} {'Eng median':>11} "
          f"{'Eng max':>9}  {'Scotland percentile rank'}")

    years = sorted(paye['year'].unique())
    for yr in years:
        eng_yr = eng[eng['year'] == yr]['overseas_share']
        scot_yr = scot[scot['year'] == yr]['overseas_share']
        if len(scot_yr) == 0 or eng_yr.isna().all():
            continue
        scot_val = scot_yr.values[0]
        pct_rank = (eng_yr < scot_val).mean() * 100
        print(f"  {yr:<6} {scot_val:>10.3f} {eng_yr.min():>9.3f} "
              f"{eng_yr.median():>11.3f} {eng_yr.max():>9.3f}  "
              f"{pct_rank:>5.0f}th percentile")

    print(f"\n{'=' * 70}")
    print("SUMMARY: 2016-2023 AVERAGE")
    print(f"{'=' * 70}")
    eng_avg = eng.groupby('region')['overseas_share'].mean()
    scot_avg = scot['overseas_share'].mean()

    print(f"  Scotland average overseas share: {scot_avg:.3f}")
    print(f"  English regions (9), average overseas share by region:")
    for region, val in eng_avg.sort_values().items():
        marker = ""
        print(f"    {region:<25} {val:.3f}")
    print(f"\n  English range: {eng_avg.min():.3f} to {eng_avg.max():.3f}, "
          f"median {eng_avg.median():.3f}")

    pct_rank_overall = (eng_avg < scot_avg).mean() * 100
    print(f"  Scotland sits at the {pct_rank_overall:.0f}th percentile "
          f"of the English regional distribution")

    print(f"\n{'=' * 70}")
    print("NOTE")
    print(f"{'=' * 70}")
    print("  Purely descriptive. If Scotland sits within the English")
    print("  range, that's consistent with similar overseas-recruitment")
    print("  dynamics UK-wide. If it's a clear outlier (well above or")
    print("  below every English region), that's a genuine 'fingerprint'")
    print("  worth flagging as a direction for future research -- e.g.")
    print("  differences in Scotland's own immigration/visa policy")
    print("  administration, geography, or sector composition -- not")
    print("  something this analysis is positioned to explain causally.")


if __name__ == '__main__':
    main()
