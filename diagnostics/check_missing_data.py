"""Check missing data patterns across all LAs and years"""
from data_loading import load_wellbeing_data
from boundaries import harmonise_boundaries
import pandas as pd

wb_raw = pd.read_csv('data/wellbeing_la.csv')

# Filter to mean estimates only
mean_only = wb_raw[wb_raw['wellbeing-estimate'].str.contains('mean|average', case=False, na=False)]

print("MISSING DATA ANALYSIS - RAW ONS DATA")
print("=" * 70)

# Find value column
value_col = 'v4_1'  # This is typically the mean value column

# Check missing by year
print("\nMissing data by year:")
for year in sorted(mean_only['yyyy-yy'].unique()):
    year_data = mean_only[mean_only['yyyy-yy'] == year]
    total = len(year_data)
    missing = year_data[value_col].isna().sum()
    pct = (missing / total * 100) if total > 0 else 0
    print(f"  {year}: {missing:4d} / {total:5d} missing ({pct:5.2f}%)")

# Check which LAs have missing data
print("\n" + "=" * 70)
print("LAs WITH MISSING DATA (any year)")
print("=" * 70)

# Get LAs with any missing
las_with_missing = []
for la in mean_only['administrative-geography'].unique():
    la_data = mean_only[mean_only['administrative-geography'] == la]
    n_missing = la_data[value_col].isna().sum()
    n_total = len(la_data)
    if n_missing > 0:
        las_with_missing.append({
            'la_code': la,
            'total_rows': n_total,
            'missing_rows': n_missing,
            'pct_missing': n_missing / n_total * 100
        })

missing_df = pd.DataFrame(las_with_missing).sort_values('missing_rows', ascending=False)

print(f"\nTotal LAs with ANY missing data: {len(missing_df)}")
print(f"\nTop 20 LAs by missing rows:")
print(missing_df.head(20).to_string(index=False))

# Check if missing is concentrated in specific LA types
print("\n" + "=" * 70)
print("PATTERN ANALYSIS")
print("=" * 70)

# Are the missing data in new codes (post-2019 creations)?
new_codes_pattern = missing_df['la_code'].str.match('E06000', na=False)
print(f"\nE06 codes (unitaries, often new): {new_codes_pattern.sum()} with missing")
old_codes_pattern = missing_df['la_code'].str.match('E07000', na=False)
print(f"E07 codes (districts, often old): {old_codes_pattern.sum()} with missing")

# Now check after our processing
print("\n" + "=" * 70)
print("AFTER data_loading.py PROCESSING")
print("=" * 70)

wb = load_wellbeing_data()
wb = harmonise_boundaries(wb)

total_obs = len(wb)
missing_obs = wb['value'].isna().sum()

print(f"Total observations: {total_obs}")
print(f"Missing values: {missing_obs} ({missing_obs/total_obs*100:.2f}%)")

if missing_obs > 0:
    print("\nLAs with missing after processing:")
    wb_missing = wb[wb['value'].isna()].groupby('la_code').size().sort_values(ascending=False)
    print(wb_missing.head(20))
