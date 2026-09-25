
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
