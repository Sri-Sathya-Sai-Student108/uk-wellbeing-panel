#!/usr/bin/env python3
"""
main.py — Trajectory analysis at supergroup/group/subgroup level.

Computes OLS trends for each LA, classifies as improving/stable/deteriorating,
aggregates by area type, and produces summary tables and plots.

Usage:
  python main.py                                # supergroup, UK
  python main.py --level group                  # 16 groups
  python main.py --england-only                 # England only
  python main.py --no-combine-splits            # Keep split codes separate
"""

import argparse
import os
import sys

from config import DATA_DIR, OUTPUT_DIR, MEASURES, MEASURE_LABELS
from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, propagate_classification, remap_scottish_codes, combine_splits
from analysis import (compute_la_trends, classify_trajectories, analyse_by_group,
                      test_group_differences, plot_trajectories, plot_slopes,
                      plot_heatmap, plot_four_panel)


def main():
    parser = argparse.ArgumentParser(description='Wellbeing trajectory analysis')
    parser.add_argument('--level', choices=['supergroup', 'group', 'subgroup'],
                        default='supergroup',
                        help='Area classification level')
    parser.add_argument('--england-only', action='store_true',
                        help='Restrict to English LAs only')
    parser.add_argument('--no-combine-splits', action='store_true',
                        help='Keep split authorities separate (default: combine to county footprints)')
    parser.add_argument('--no-weighting', action='store_true',
                        help='Use unweighted OLS (default: WLS with inverse-variance weights)')
    parser.add_argument('--no-hac', action='store_true',
                        help='Disable Newey-West HAC clustering (default: use HAC for autocorrelation-robust SEs)')
    parser.add_argument('--pre-covid', action='store_true',
                        help='Restrict analysis to pre-COVID period (2011-2019 only)')
    args = parser.parse_args()

    # Setup
    os.makedirs(DATA_DIR, exist_ok=True)
    
    dir_name = f"{args.level}_england" if args.england_only else args.level
    out_dir = os.path.join(OUTPUT_DIR, dir_name)
    os.makedirs(os.path.join(out_dir, 'tables'), exist_ok=True)
    os.makedirs(os.path.join(out_dir, 'plots'), exist_ok=True)

    print("=" * 70)
    print("LONGITUDINAL ANALYSIS OF ONS PERSONAL WELL-BEING")
    print(f"BY ONS 2011 AREA CLASSIFICATION — {args.level.upper()} LEVEL")
    scope = "England" if args.england_only else "UK"
    print(f"Scope: {scope}")
    if not args.no_combine_splits:
        print("Combining county splits to maintain historic geography")
    weighting_method = "Unweighted OLS" if args.no_weighting else "WLS (inverse-variance)"
    if not args.no_weighting and not args.no_hac:
        weighting_method += " + Newey-West HAC"
    print(f"Estimation: {weighting_method}")
    print("=" * 70)

    # Check data files exist
    if not check_data_files():
        return

    # Load wellbeing data
    wb_df = load_wellbeing_data()
    wb_df = harmonise_boundaries(wb_df)
    
    # Load classification
    class_df = load_area_classification()
    class_df = propagate_classification(class_df)
    
    # Remap Scottish codes
    wb_df = remap_scottish_codes(wb_df)
    class_df = remap_scottish_codes(class_df)
    
    # Combine county splits by default (maintains historic geography for linkage)
    if not args.no_combine_splits:
        wb_df = combine_splits(wb_df)
        class_df = combine_splits(class_df)
    
    # Filter to England if requested
    if args.england_only:
        wb_df = wb_df[wb_df['la_code'].str.startswith('E')]
        class_df = class_df[class_df['la_code'].str.startswith('E')]
    
    # Filter to pre-COVID period if requested
    if args.pre_covid:
        wb_df = wb_df[wb_df['year'] <= 2019]
        print("Filtered to pre-COVID period (2011-2019)")

    # Open report file
    report_path = os.path.join(out_dir, 'tables', 'report.txt')
    with open(report_path, 'w') as report:
        report.write("LONGITUDINAL ANALYSIS OF ONS PERSONAL WELL-BEING\n")
        report.write(f"BY ONS 2011 AREA CLASSIFICATION — {args.level.upper()} LEVEL\n")
        report.write(f"Scope: {scope}\n")
        if not args.no_combine_splits:
            report.write("County splits combined to historic footprints\n")
        report.write("\n")
        
        # Document boundary handling
        report.write("Boundary mergers applied (population-weighted means):\n")
        from boundaries import BOUNDARY_MERGES
        for code, info in sorted(BOUNDARY_MERGES.items(), key=lambda x: x[1]['year']):
            n_pred = len(info['predecessors'])
            report.write(f"  {info['name']}: {n_pred} predecessors [{info['year']}]\n")
        
        if not args.no_combine_splits:
            report.write("\nCounty splits combined (equal-weighted means):\n")
            from boundaries import BOUNDARY_SPLITS
            for code, info in BOUNDARY_SPLITS.items():
                n_parts = len(info['split_parts'])
                report.write(f"  {info['name']}: {n_parts} parts [{info['year']}]\n")
        
        report.write("\n\n")

        # Analyse each measure
        for measure in MEASURES:
            print(f"\n{'=' * 70}")
            print(f"{MEASURE_LABELS[measure].upper()}")
            print('=' * 70)

            report.write(f"{MEASURE_LABELS[measure].upper()}\n")
            report.write("-" * 50 + "\n")

            # Compute trends
            trends = compute_la_trends(wb_df, measure=measure, min_years=6,
                                      weighted=not args.no_weighting,
                                      hac=not args.no_hac)
            if len(trends) == 0:
                print(f"  No trends computed for {measure}")
                continue

            # Classify trajectories
            classified = classify_trajectories(trends)
            
            # Reverse anxiety interpretation (lower is better)
            if measure == 'anxiety':
                swap = {'Improving': 'Deteriorating', 'Deteriorating': 'Improving'}
                classified['trajectory'] = classified['trajectory'].map(
                    lambda x: swap.get(x, x))

            # Aggregate by area type
            merged, summary = analyse_by_group(classified, class_df, 
                                              group_col=args.level)
            
            if summary is None:
                print(f"  No summary for {measure}")
                continue

            # Print and save summary
            print(summary)
            report.write(summary.to_string())
            report.write("\n\n")

            # Statistical tests
            test_group_differences(classified, class_df, group_col=args.level)

            # Plots
            plot_dir = os.path.join(out_dir, 'plots')
            plot_trajectories(wb_df, class_df, measure, group_col=args.level,
                            output_dir=plot_dir)
            plot_slopes(classified, class_df, measure, group_col=args.level,
                       output_dir=plot_dir)
            plot_heatmap(summary, measure, group_col=args.level,
                        output_dir=plot_dir)

            # Save detailed results
            excel_path = os.path.join(out_dir, 'tables', 
                                     f'wellbeing_trajectories_{measure}.xlsx')
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                summary.to_excel(writer, sheet_name='Summary')
                merged.to_excel(writer, sheet_name='LA_level', index=False)
            print(f"  Saved: {excel_path}")

    # Four-panel plot (all measures)
    print("\nGenerating four-panel plot...")
    plot_four_panel(wb_df, class_df, group_col=args.level,
                   output_dir=os.path.join(out_dir, 'plots'))

    # Summary
    print("\n" + "=" * 70)
    print(f"DONE. Outputs in {out_dir}/")
    print("=" * 70)
    print(f"\nReport: {report_path}")
    print(f"Plots: {os.path.join(out_dir, 'plots')}/")
    print(f"Tables: {os.path.join(out_dir, 'tables')}/")


if __name__ == '__main__':
    # Need pandas for Excel writing
    import pandas as pd
    main()
