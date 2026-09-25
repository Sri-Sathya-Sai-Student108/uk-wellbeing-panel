#!/usr/bin/env python3
"""
export_curated.py — Export curated datasets for distribution.

Creates analysis-ready CSV files that users can download and use directly
without running the full boundary harmonisation pipeline.

Outputs:
  data/curated/wellbeing_harmonised_panel.csv  - Full panel (354 LAs x 12 years x 4 measures)
  data/curated/area_classification_354.csv     - Classification for 354 harmonised LAs
  data/curated/trajectory_results_supergroup.csv - Trajectory classifications by supergroup
  data/curated/trajectory_results_group.csv      - Trajectory classifications by group
  data/curated/trajectory_results_subgroup.csv   - Trajectory classifications by subgroup
  data/curated/la_level_trajectories.csv         - Individual LA trajectories (all measures)

Usage:
  python export_curated.py
"""

import os
import pandas as pd
from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, propagate_classification, remap_scottish_codes, combine_splits
from analysis import compute_la_trends, classify_trajectories, analyse_by_group
from config import MEASURES

CURATED_DIR = os.path.join('data', 'curated')


def export_curated_datasets():
    """Export all curated datasets for distribution."""
    
    # Setup
    os.makedirs(CURATED_DIR, exist_ok=True)
    
    print("=" * 70)
    print("EXPORTING CURATED DATASETS FOR DISTRIBUTION")
    print("=" * 70)
    
    if not check_data_files():
        print("ERROR: Source data files missing. Download first.")
        return
    
    # 1. Load and harmonise wellbeing data
    print("\n1. Processing wellbeing panel...")
    wb_df = load_wellbeing_data()
    wb_df = harmonise_boundaries(wb_df)
    wb_df = remap_scottish_codes(wb_df)
    wb_df = combine_splits(wb_df)
    
    # Export harmonised panel
    panel_path = os.path.join(CURATED_DIR, 'wellbeing_harmonised_panel.csv')
    wb_df.to_csv(panel_path, index=False)
    print(f"   Saved: {panel_path}")
    print(f"   {len(wb_df)} observations, {wb_df['la_code'].nunique()} LAs")
    
    # 2. Load and process classification
    print("\n2. Processing area classification...")
    class_df = load_area_classification()
    class_df = propagate_classification(class_df)
    class_df = remap_scottish_codes(class_df)
    class_df = combine_splits(class_df)
    
    # Export classification
    class_path = os.path.join(CURATED_DIR, 'area_classification_354.csv')
    class_df.to_csv(class_path, index=False)
    print(f"   Saved: {class_path}")
    print(f"   {len(class_df)} LAs classified")
    
    # 3. Compute and export trajectories for all measures
    print("\n3. Computing trajectory classifications...")
    
    all_la_trajectories = []
    
    for measure in MEASURES:
        print(f"\n   {measure}...")
        
        # Compute trends
        trends = compute_la_trends(wb_df, measure=measure, min_years=6)
        if len(trends) == 0:
            continue
        
        # Classify trajectories
        classified = classify_trajectories(trends)
        
        # Reverse anxiety
        if measure == 'anxiety':
            swap = {'Improving': 'Deteriorating', 'Deteriorating': 'Improving'}
            classified['trajectory'] = classified['trajectory'].map(
                lambda x: swap.get(x, x))
        
        # Add measure column
        classified['measure'] = measure
        all_la_trajectories.append(classified)
        
        # Aggregate by supergroup/group/subgroup
        for level in ['supergroup', 'group', 'subgroup']:
            merged, summary = analyse_by_group(classified, class_df, group_col=level)
            
            if summary is not None:
                summary_path = os.path.join(CURATED_DIR, 
                                           f'trajectory_results_{level}.csv')
                
                # Add measure column
                summary['measure'] = measure
                
                # Append to existing file or create new
                if os.path.exists(summary_path):
                    existing = pd.read_csv(summary_path)
                    combined = pd.concat([existing, summary.reset_index()], 
                                        ignore_index=True)
                    combined.to_csv(summary_path, index=False)
                else:
                    summary.reset_index().to_csv(summary_path, index=False)
    
    # Export LA-level trajectories (all measures combined)
    if all_la_trajectories:
        la_traj = pd.concat(all_la_trajectories, ignore_index=True)
        la_path = os.path.join(CURATED_DIR, 'la_level_trajectories.csv')
        la_traj.to_csv(la_path, index=False)
        print(f"\n   Saved: {la_path}")
        print(f"   {len(la_traj)} LA-measure trajectories")
    
    # 4. Create data dictionary
    print("\n4. Creating data dictionary...")
    
    data_dict = """
# Curated Wellbeing Trajectory Datasets

This directory contains analysis-ready datasets from the ONS wellbeing trajectory project.
These files can be used directly without running the boundary harmonisation pipeline.

## Files

### wellbeing_harmonised_panel.csv
Harmonised wellbeing panel with boundary changes handled.

Columns:
- la_code: Local authority code (354 harmonised LAs)
- la_name: Local authority name
- measure: Wellbeing measure (life-satisfaction, worthwhile, happiness, anxiety)
- value: Mean score (0-10 scale)
- period: ONS time period (e.g., "2011-12")
- year: Year (2011-2022)

Rows: 16,992 (354 LAs × 12 years × 4 measures)

### area_classification_354.csv
ONS 2011 Area Classification for the 354 harmonised LAs.

Columns:
- la_code: Local authority code
- supergroup_code: Supergroup code (1-8)
- supergroup: Supergroup name (8 categories)
- group_code: Group code (1a-8b)
- group: Group name (16 categories)
- subgroup_code: Subgroup code
- subgroup: Subgroup name (24 categories)

Rows: 354

Note: For combined county splits (DORSET_COMBINED, NORTHANTS_COMBINED, CUMBRIA_COMBINED),
classifications are manually assigned based on county character - see paper Methods section.

### la_level_trajectories.csv
Individual LA trajectory classifications for all four measures.

Columns:
- la_code, la_name: Local authority identifiers
- measure: Wellbeing measure
- slope: Annual trend (OLS slope, points/year)
- intercept, r_squared, p_value, std_err: Regression statistics
- start_value, end_value, total_change: Summary statistics
- n_years, year_start, year_end: Time coverage
- trajectory: Classification (Improving/Stable/Deteriorating)

Rows: ~1,400 (354 LAs × 4 measures, excluding LAs with <6 years)

### trajectory_results_supergroup.csv
Aggregate trajectory statistics by supergroup (8 groups).

Columns:
- supergroup: Area type name
- measure: Wellbeing measure
- n_las: Number of LAs in this supergroup
- mean_baseline: Mean score in 2011/12
- mean_slope, median_slope, std_slope: Trend statistics
- mean_change: Mean total change 2011-2022
- pct_improving, pct_stable, pct_deteriorating: Trajectory distribution

Rows: 32 (8 supergroups × 4 measures)

### trajectory_results_group.csv
As above, for 16 groups. Rows: 64 (16 × 4)

### trajectory_results_subgroup.csv
As above, for 24 subgroups. Rows: 96 (24 × 4)

## Usage Example

```python
import pandas as pd

# Load harmonised panel
wb = pd.read_csv('data/curated/wellbeing_harmonised_panel.csv')

# Load classification
cl = pd.read_csv('data/curated/area_classification_354.csv')

# Merge
df = wb.merge(cl[['la_code', 'supergroup']], on='la_code')

# Analyse
life_sat = df[df['measure'] == 'life-satisfaction']
print(life_sat.groupby('supergroup')['value'].mean())
```

## Citation

If you use these datasets, please cite:

[Author names] (2026). A Harmonised Longitudinal Panel of Local Authority 
Well-being in the United Kingdom, 2011-2023: Dataset Construction and 
Trajectory Analysis. [Journal].

Data and code: [OSF/GitHub URL]

## License

Open Government Licence v3.0 (underlying ONS data)
MIT License (harmonisation code and curated datasets)
"""
    
    dict_path = os.path.join(CURATED_DIR, 'README.md')
    with open(dict_path, 'w') as f:
        f.write(data_dict)
    print(f"   Saved: {dict_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"\nCurated datasets exported to: {CURATED_DIR}/")
    print("\nFiles created:")
    for f in os.listdir(CURATED_DIR):
        path = os.path.join(CURATED_DIR, f)
        size = os.path.getsize(path) / 1024
        print(f"  {f:45s} {size:8.1f} KB")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Review the exported files
2. Zip the curated/ directory for distribution
3. Upload to OSF/Figshare/GitHub releases
4. Add DOI to paper
5. Update paper Data Availability section with direct download link
""")


if __name__ == '__main__':
    export_curated_datasets()
