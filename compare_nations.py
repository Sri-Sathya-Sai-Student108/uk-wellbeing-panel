"""Compare wellbeing trajectories across England, Scotland, Wales, Northern Ireland"""
from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, propagate_classification, remap_scottish_codes, combine_splits
from analysis import compute_la_trends, classify_trajectories
from config import MEASURES, MEASURE_LABELS
import pandas as pd

if not check_data_files():
    exit()

# Load data
wb_df = load_wellbeing_data()
wb_df = harmonise_boundaries(wb_df)
wb_df = remap_scottish_codes(wb_df)
wb_df = combine_splits(wb_df)

class_df = load_area_classification()
class_df = propagate_classification(class_df)
class_df = remap_scottish_codes(class_df)
class_df = combine_splits(class_df)

# Add nation indicator
def get_nation(code):
    if code.startswith('E'):
        return 'England'
    elif code.startswith('S'):
        return 'Scotland'
    elif code.startswith('W'):
        return 'Wales'
    elif code.startswith('N'):
        return 'Northern Ireland'
    elif code.startswith('DORSET') or code.startswith('NORTHANTS') or code.startswith('CUMBRIA'):
        return 'England'  # Combined counties
    else:
        return 'Unknown'

wb_df['nation'] = wb_df['la_code'].apply(get_nation)

print("=" * 70)
print("WELLBEING TRAJECTORIES BY NATION")
print("=" * 70)

for measure in MEASURES:
    print(f"\n{MEASURE_LABELS[measure].upper()}")
    print("-" * 70)
    
    # Compute trends
    trends = compute_la_trends(wb_df, measure=measure, min_years=6)
    if len(trends) == 0:
        continue
    
    classified = classify_trajectories(trends)
    
    # Reverse anxiety
    if measure == 'anxiety':
        swap = {'Improving': 'Deteriorating', 'Deteriorating': 'Improving'}
        classified['trajectory'] = classified['trajectory'].map(lambda x: swap.get(x, x))
    
    # Add nation
    classified['nation'] = classified['la_code'].apply(get_nation)
    
    # Aggregate by nation
    summary = classified.groupby('nation').agg(
        n_las=('la_code', 'count'),
        mean_baseline=('start_value', 'mean'),
        mean_slope=('slope', 'mean'),
        median_slope=('slope', 'median'),
        pct_improving=('trajectory', lambda x: (x == 'Improving').mean() * 100),
        pct_stable=('trajectory', lambda x: (x == 'Stable').mean() * 100),
        pct_deteriorating=('trajectory', lambda x: (x == 'Deteriorating').mean() * 100),
    ).round(3)
    
    print(summary.to_string())

print("\n" + "=" * 70)
print("INTERPRETATION NOTES")
print("=" * 70)
print("""
Look for:
1. Baseline differences - do nations start at different levels?
2. Slope patterns - which nations improving/deteriorating fastest?
3. Trajectory distribution - what % improving/stable/deteriorating?

Key comparisons:
- England vs Scotland: Similar or different patterns?
- Wales: Small sample (22 LAs) but distinct trajectory?
- Northern Ireland: Smallest sample (15 LAs) - any outlier patterns?

For the paper, focus on:
- Where national patterns DIFFER from UK aggregate
- Specific findings (e.g., "Northern Ireland Countryside deteriorating")
- Whether devolved policies might explain differences
""")

# Additional analysis: Check for nation-specific area type patterns
print("\n" + "=" * 70)
print("NATION-SPECIFIC AREA TYPE PATTERNS")
print("=" * 70)

# Merge with classification to get supergroup
trends = compute_la_trends(wb_df, measure='life-satisfaction', min_years=6)
classified = classify_trajectories(trends)
classified['nation'] = classified['la_code'].apply(get_nation)

merged_with_class = classified.merge(class_df[['la_code', 'supergroup']], 
                                     on='la_code', how='inner')

print("\nLife Satisfaction by Nation × Supergroup:")
nation_sg = merged_with_class.groupby(['nation', 'supergroup']).agg(
    n=('la_code', 'count'),
    mean_baseline=('start_value', 'mean'),
    mean_slope=('slope', 'mean'),
    pct_improving=('trajectory', lambda x: (x == 'Improving').mean() * 100),
    pct_deteriorating=('trajectory', lambda x: (x == 'Deteriorating').mean() * 100)
).round(3)

print(nation_sg.to_string())

# Do the same for all 4 measures
print("\n" + "=" * 70)
print("DETAILED BREAKDOWN BY MEASURE")
print("=" * 70)

for measure in MEASURES:
    print(f"\n{MEASURE_LABELS[measure].upper()} by Nation × Supergroup")
    print("-" * 70)
    
    trends_m = compute_la_trends(wb_df, measure=measure, min_years=6)
    classified_m = classify_trajectories(trends_m)
    
    # Reverse anxiety
    if measure == 'anxiety':
        swap = {'Improving': 'Deteriorating', 'Deteriorating': 'Improving'}
        classified_m['trajectory'] = classified_m['trajectory'].map(lambda x: swap.get(x, x))
    
    classified_m['nation'] = classified_m['la_code'].apply(get_nation)
    
    merged_m = classified_m.merge(class_df[['la_code', 'supergroup']], 
                                  on='la_code', how='inner')
    
    # Show only cells with n>=3 to avoid unstable estimates
    nation_sg_m = merged_m.groupby(['nation', 'supergroup']).agg(
        n=('la_code', 'count'),
        mean_slope=('slope', 'mean'),
        pct_improving=('trajectory', lambda x: (x == 'Improving').mean() * 100)
    ).round(3)
    
    # Filter to n>=3 for stability
    nation_sg_m_filtered = nation_sg_m[nation_sg_m['n'] >= 3]
    
    if len(nation_sg_m_filtered) > 0:
        print(nation_sg_m_filtered.to_string())
    else:
        print("  (All cells have n<3 - too small for reliable estimates)")

print("\n" + "=" * 70)
print("NOTABLE PATTERNS")
print("=" * 70)
print("""
Look for:
- Supergroups that appear in multiple nations - do they show similar trends?
- Nation-specific supergroups (e.g., Scottish Countryside, NI Countryside)
- Divergent patterns (same supergroup, different trajectory in different nations)

KEY FINDINGS TO HIGHLIGHT IN PAPER:

1. SCOTLAND vs ENGLAND Countryside:
   - Do rural areas in Scotland follow same pattern as English rural?
   - Check Scottish Countryside vs English/Welsh Countryside

2. SERVICES & INDUSTRIAL LEGACY across nations:
   - This supergroup appears in Scotland, Wales, England
   - Do post-industrial areas show similar recovery across nations?

3. NORTHERN IRELAND concentration:
   - Most NI LAs are Town and Country Living (rural)
   - This drives the national NI deterioration pattern

4. SAMPLE SIZE LIMITATIONS:
   - Scotland: 32 LAs → maybe 3-5 per supergroup
   - Wales: 22 LAs → maybe 2-4 per supergroup  
   - NI: 11 LAs → mostly one supergroup
   - For paper: note that nation-specific analyses limited by sample
""")
