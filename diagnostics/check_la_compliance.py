#!/usr/bin/env python3
"""
check_la_compliance.py - Does compliance strength (first-stage F)
differ between high- and low-overseas LA groups?

Motivation: today's regional-level work found the low-overseas group's
first stage was essentially unidentified (F=0.32) while the high-
overseas group was solid (F=16.35) -- consistent with low-overseas
regions being "non-compliers" in the LATE sense (their retail growth
doesn't track what the Bartik instrument predicts, so a 2SLS estimate
is concentrated on the high-overseas group and tells us little about
the low-overseas one). But that comparison was only ever possible at
N=9 regions.

This extends the same question to the full 148-LA sample: classify
each LA as high/low overseas access based on its REGION's overseas
share (same broadcast-down variable used throughout, but here used only
to sort LAs into two large compliance-comparison groups, not as a
regressor), then run the FIRST STAGE ONLY, separately in each group --
no second stage, purely testing whether compliance strength itself
varies by group, with real statistical power (dozens of LAs per group,
not 4-5 regions).

Reuses first_stage() from bartik_check.py UNCHANGED on each subsample.

Usage:
  python check_la_compliance.py
"""

import os
import sys
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bartik_check import load_data, construct_bartik, first_stage


def main():
    df = load_data()
    df = construct_bartik(df)

    if 'overseas_share' not in df.columns:
        print("\nERROR: 'overseas_share' column not found in the LA panel.")
        print("Check assemble_england_sfc.py to confirm how/whether PAYE")
        print("overseas_share is merged in at LA level before proceeding.")
        return

    eng = df[~df['region'].isin(['Scotland', 'Wales', 'Northern Ireland'])].copy()

    # Same classification logic as the earlier (now-removed) LA-level
    # heterogeneity section: median split on each region's average
    # overseas_share, applied to every LA in that region.
    median_share = eng.groupby('region')['overseas_share'].mean().median()
    df['high_visa'] = df['overseas_share'] > median_share

    low_df = df[~df['high_visa']].copy()
    high_df = df[df['high_visa']].copy()

    print(f"\nMedian overseas share across English regions: {median_share:.3f}")
    print(f"LOW overseas LAs:  {low_df['la_code'].nunique()}")
    print(f"HIGH overseas LAs: {high_df['la_code'].nunique()}")

    print(f"\n{'#' * 70}")
    print("# LOW OVERSEAS LAs -- FIRST STAGE ONLY")
    print(f"{'#' * 70}")
    f_low, coef_low = first_stage(low_df)

    print(f"\n{'#' * 70}")
    print("# HIGH OVERSEAS LAs -- FIRST STAGE ONLY")
    print(f"{'#' * 70}")
    f_high, coef_high = first_stage(high_df)

    print(f"\n{'=' * 70}")
    print("COMPLIANCE COMPARISON")
    print(f"{'=' * 70}")
    print(f"  LOW overseas:  F={f_low:.2f}, N={low_df['la_code'].nunique()} LAs")
    print(f"  HIGH overseas: F={f_high:.2f}, N={high_df['la_code'].nunique()} LAs")
    print()
    print("  This is a first-stage-only diagnostic -- no second stage,")
    print("  no outcome regression. It only asks whether the instrument")
    print("  predicts retail growth equally well in both groups. If F")
    print("  differs substantially, that's evidence of differential")
    print("  compliance (LATE weighting toward whichever group has the")
    print("  stronger first stage) with real statistical power behind")
    print("  it -- unlike the N=9 regional version, this uses the full")
    print("  148-LA sample split into two large subgroups.")


if __name__ == '__main__':
    main()
