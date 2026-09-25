"""Find all LA codes that exist in classification but not in boundaries (and vice versa)"""
import geopandas as gpd
from data_loading import load_area_classification
from boundaries import propagate_classification, combine_splits

# Load both datasets
print("Loading data...")
class_df = load_area_classification()
class_df = propagate_classification(class_df)
class_df = combine_splits(class_df)

gdf = gpd.read_file('data/la_boundaries_lad23.geojson')

# Find code column in boundaries
code_col = 'LAD23CD'  # We know this from earlier

# Get unique codes from each
class_codes = set(class_df['la_code'].unique())
bound_codes = set(gdf[code_col].unique())

# Find mismatches
in_class_not_bound = class_codes - bound_codes
in_bound_not_class = bound_codes - class_codes

print("=" * 70)
print("CODES IN CLASSIFICATION BUT NOT IN BOUNDARIES")
print("=" * 70)
print(f"Total: {len(in_class_not_bound)}")
print()

# Filter to English E07 codes (district level where renumbering happened)
e07_old = sorted([c for c in in_class_not_bound if c.startswith('E07')])
print(f"E07 (district) codes: {len(e07_old)}")
for code in e07_old[:20]:  # Show first 20
    print(f"  {code}")
if len(e07_old) > 20:
    print(f"  ... and {len(e07_old) - 20} more")

print("\n" + "=" * 70)
print("CODES IN BOUNDARIES BUT NOT IN CLASSIFICATION")
print("=" * 70)
print(f"Total: {len(in_bound_not_class)}")
print()

e07_new = sorted([c for c in in_bound_not_class if c.startswith('E07')])
print(f"E07 (district) codes: {len(e07_new)}")
for code in e07_new[:20]:
    print(f"  {code}")
if len(e07_new) > 20:
    print(f"  ... and {len(e07_new) - 20} more")

print("\n" + "=" * 70)
print("ANALYSIS")
print("=" * 70)
print(f"""
Classification has {len(e07_old)} E07 codes not in boundaries (old codes)
Boundaries has {len(e07_new)} E07 codes not in classification (new codes)

If these numbers are similar, it suggests a systematic renumbering.
We need to create a mapping between old and new codes.

This affects ONLY the maps (visualization), not the analysis, because:
- Wellbeing data uses new codes (matches boundaries)
- Classification file uses old codes
- Analysis merges wellbeing + classification successfully
- BUT maps can't merge classification + boundaries
""")

# Check if wellbeing data uses new or old codes
from data_loading import load_wellbeing_data
wb_df = load_wellbeing_data()

wb_codes = set(wb_df['la_code'].unique())
wb_has_old = len(wb_codes & in_class_not_bound)
wb_has_new = len(wb_codes & in_bound_not_class)

print(f"\nWellbeing data check:")
print(f"  Has {wb_has_old} old E07 codes (from classification)")
print(f"  Has {wb_has_new} new E07 codes (from boundaries)")
print(f"  → Wellbeing uses {'NEW' if wb_has_new > wb_has_old else 'OLD'} codes")
