"""Check if combined counties have trajectory classifications"""
from data_loading import load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, propagate_classification, remap_scottish_codes, combine_splits
from analysis import compute_la_trends, classify_trajectories

# Load and process data
wb = load_wellbeing_data()
wb = harmonise_boundaries(wb)
wb = remap_scottish_codes(wb)
wb = combine_splits(wb)

class_df = load_area_classification()
class_df = propagate_classification(class_df)
class_df = remap_scottish_codes(class_df)
class_df = combine_splits(class_df)

print("CHECKING COMBINED COUNTIES IN DATA")
print("=" * 70)

combined_codes = ['DORSET_COMBINED', 'NORTHANTS_COMBINED', 'CUMBRIA_COMBINED']

for code in combined_codes:
    wb_data = wb[wb['la_code'] == code]
    class_data = class_df[class_df['la_code'] == code]
    
    print(f"\n{code}:")
    print(f"  In wellbeing data: {len(wb_data)} rows")
    if len(wb_data) > 0:
        years = sorted(wb_data['year'].unique())
        print(f"    Years: {len(years)} ({min(years)}-{max(years)})")
        measures = wb_data['measure'].unique()
        print(f"    Measures: {len(measures)}")
    
    print(f"  In classification: {len(class_data)} rows")
    if len(class_data) > 0 and 'supergroup' in class_data.columns:
        print(f"    Supergroup: {class_data['supergroup'].iloc[0]}")

print("\n" + "=" * 70)
print("TRAJECTORY CLASSIFICATION")
print("=" * 70)

# Compute trends
trends = compute_la_trends(wb, measure='life-satisfaction', min_years=6)

for code in combined_codes:
    traj = trends[trends['la_code'] == code]
    if len(traj) > 0:
        print(f"\n{code}:")
        print(f"  ✓ HAS trajectory")
        print(f"    Slope: {traj['slope'].iloc[0]:.4f}")
        print(f"    Years: {traj['n_years'].iloc[0]}")
    else:
        print(f"\n{code}:")
        print(f"  ✗ NO trajectory (insufficient data or compute failed)")

# Check what happens after classify
classified = classify_trajectories(trends)

for code in combined_codes:
    traj = classified[classified['la_code'] == code]
    if len(traj) > 0:
        print(f"\n{code} classification:")
        print(f"  Trajectory: {traj['trajectory'].iloc[0]}")
    else:
        print(f"\n{code}: Not in classified results")

# Final merge with classification (what maps.py does)
print("\n" + "=" * 70)
print("MERGE WITH CLASSIFICATION (for mapping)")
print("=" * 70)

merged = classified.merge(class_df[['la_code', 'supergroup']], on='la_code', how='left')

for code in combined_codes:
    final = merged[merged['la_code'] == code]
    if len(final) > 0:
        print(f"\n{code}:")
        print(f"  ✓ In final merged data")
        print(f"  Trajectory: {final['trajectory'].iloc[0]}")
        print(f"  Supergroup: {final['supergroup'].iloc[0] if 'supergroup' in final.columns else 'N/A'}")
    else:
        print(f"\n{code}: MISSING from final merge!")
