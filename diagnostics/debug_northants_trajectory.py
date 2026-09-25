"""Debug why NORTHANTS_COMBINED trajectory computation fails"""
from data_loading import load_wellbeing_data
from boundaries import harmonise_boundaries, remap_scottish_codes, combine_splits
import pandas as pd
from scipy import stats

wb = load_wellbeing_data()
wb = harmonise_boundaries(wb)
wb = remap_scottish_codes(wb)
wb = combine_splits(wb)

# Get NORTHANTS_COMBINED data
northants = wb[wb['la_code'] == 'NORTHANTS_COMBINED']

print("NORTHANTS_COMBINED DATA")
print("=" * 70)
print(f"Total rows: {len(northants)}")
print(f"\nBreakdown:")
print(northants.groupby('measure').size())

# Check life-satisfaction specifically
ls = northants[northants['measure'] == 'life-satisfaction'].copy()
print(f"\nLife satisfaction rows: {len(ls)}")
print(ls[['year', 'value']].sort_values('year'))

# Try to compute OLS manually
print("\n" + "=" * 70)
print("MANUAL OLS COMPUTATION")
print("=" * 70)

ls = ls.dropna(subset=['value']).sort_values('year')
print(f"After dropna: {len(ls)} rows")

if len(ls) >= 6:
    x = ls['year'].values
    y = ls['value'].values
    
    print(f"X (years): {x}")
    print(f"Y (values): {y}")
    
    # Check for NaN or inf
    print(f"\nAny NaN in Y? {pd.isna(y).any()}")
    print(f"Any inf in Y? {any(v == float('inf') or v == float('-inf') for v in y)}")
    
    try:
        slope, intercept, r_val, p_val, se = stats.linregress(x, y)
        print(f"\n✓ OLS succeeded:")
        print(f"  Slope: {slope}")
        print(f"  R²: {r_val**2}")
        print(f"  p-value: {p_val}")
    except Exception as e:
        print(f"\n✗ OLS failed: {e}")
else:
    print(f"✗ Insufficient data: {len(ls)} < 6 years")

# Compare with a working LA
print("\n" + "=" * 70)
print("COMPARISON: Check a working LA")
print("=" * 70)

# Try Leeds (should definitely work)
leeds = wb[wb['la_code'] == 'E08000035']
if len(leeds) > 0:
    leeds_ls = leeds[leeds['measure'] == 'life-satisfaction']
    print(f"Leeds (E08000035): {len(leeds_ls)} rows")
    print(leeds_ls[['year', 'value']].sort_values('year'))
