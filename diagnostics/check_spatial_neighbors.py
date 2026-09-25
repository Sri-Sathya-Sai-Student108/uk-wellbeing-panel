"""
Analyze geographic neighbor patterns in wellbeing trajectories.

Uses geopandas to identify neighbors, then checks if neighboring LAs
have correlated slopes.
"""

from data_loading import check_data_files, load_wellbeing_data
from boundaries import harmonise_boundaries, remap_scottish_codes, combine_splits
from analysis import compute_la_trends
from config import MEASURES, MEASURE_LABELS
import pandas as pd
import numpy as np
from scipy import stats
import geopandas as gpd

print("=" * 70)
print("SPATIAL NEIGHBOR ANALYSIS")
print("=" * 70)

if not check_data_files():
    exit()

# Load data
wb_df = load_wellbeing_data()
wb_df = harmonise_boundaries(wb_df)
wb_df = remap_scottish_codes(wb_df)
wb_df = combine_splits(wb_df)

# Load boundaries
print("\nLoading boundaries...")
gdf = gpd.read_file('data/la_boundaries_lad23.geojson')
code_col = 'LAD23CD'

# Combine splits
from maps import combine_boundary_splits
gdf = combine_boundary_splits(gdf, code_col)

print(f"  {len(gdf)} LA boundaries")

# Identify neighbors using touches
print("\nIdentifying neighbors (shared boundaries)...")

neighbors_dict = {}

for idx, row in gdf.iterrows():
    la_code = row[code_col]
    geom = row.geometry
    
    # Find all LAs that touch this one
    touching = gdf[gdf.geometry.touches(geom)]
    neighbor_codes = touching[code_col].tolist()
    
    neighbors_dict[la_code] = neighbor_codes

n_with_neighbors = sum(1 for v in neighbors_dict.values() if len(v) > 0)
mean_neighbors = np.mean([len(v) for v in neighbors_dict.values()])

print(f"  {n_with_neighbors} LAs have neighbors")
print(f"  Mean neighbors per LA: {mean_neighbors:.1f}")

# For each measure, check neighbor correlation
print("\n" + "=" * 70)
print("NEIGHBOR SLOPE CORRELATIONS")
print("=" * 70)

for measure in MEASURES:
    print(f"\n{MEASURE_LABELS[measure]}:")
    
    trends = compute_la_trends(wb_df, measure=measure, min_years=6, weighted=True)
    slopes_dict = dict(zip(trends['la_code'], trends['slope']))
    
    # Collect (LA slope, mean neighbor slope) pairs
    pairs = []
    
    for la_code, neighbor_codes in neighbors_dict.items():
        if la_code in slopes_dict and len(neighbor_codes) > 0:
            la_slope = slopes_dict[la_code]
            
            # Get neighbor slopes
            neighbor_slopes = [slopes_dict[n] for n in neighbor_codes 
                              if n in slopes_dict]
            
            if len(neighbor_slopes) > 0:
                mean_neighbor_slope = np.mean(neighbor_slopes)
                pairs.append((la_slope, mean_neighbor_slope))
    
    if len(pairs) > 10:
        own_slopes = [p[0] for p in pairs]
        neighbor_slopes = [p[1] for p in pairs]
        
        r, p = stats.pearsonr(own_slopes, neighbor_slopes)
        
        print(f"  {len(pairs)} LA-neighbor pairs")
        print(f"  Correlation: r = {r:.3f}, p = {p:.4f}")
        
        if p < 0.05:
            if r > 0:
                print(f"  ✓ Significant positive correlation")
                print(f"    → LAs improve/decline with their neighbors")
            else:
                print(f"  ✗ Significant negative correlation")
        else:
            print(f"  ✗ No significant spatial correlation")

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)
print("""
Positive spatial correlation (r > 0.3):
→ Neighboring LAs have similar trajectories
→ Suggests spillovers, common shocks, or regional patterns
→ Standard errors in panel models should account for spatial clustering

No spatial correlation (r ≈ 0):
→ Trajectories are LA-specific
→ Standard LA-level clustering sufficient

For full spatial econometrics (Moran's I, spatial lag models):
  pip install libpysal esda
Then re-run for formal spatial autocorrelation tests.
""")
