"""
Test whether spatial correlation is real spillover or classification artifact.

If neighbor correlation disappears after controlling for area type, it's just
that similar types cluster geographically (not true spillover).

If it persists WITHIN area types, it's genuine spatial spillover.
"""

from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, remap_scottish_codes, combine_splits, propagate_classification
from analysis import compute_la_trends
from config import MEASURES, MEASURE_LABELS
import pandas as pd
import numpy as np
from scipy import stats
import geopandas as gpd

print("=" * 70)
print("SPATIAL CORRELATION: SPILLOVER VS CLASSIFICATION ARTIFACT")
print("=" * 70)

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

# Load boundaries
print("\nLoading boundaries...")
gdf = gpd.read_file('data/la_boundaries_lad23.geojson')
code_col = 'LAD23CD'

from maps import combine_boundary_splits
gdf = combine_boundary_splits(gdf, code_col)

# Identify neighbors
print("\nIdentifying neighbors...")
neighbors_dict = {}

for idx, row in gdf.iterrows():
    la_code = row[code_col]
    geom = row.geometry
    touching = gdf[gdf.geometry.touches(geom)]
    neighbors_dict[la_code] = touching[code_col].tolist()

print(f"  {len(neighbors_dict)} LAs with neighbor info")

# Test for each measure
for measure in MEASURES:
    print("\n" + "=" * 70)
    print(f"{MEASURE_LABELS[measure].upper()}")
    print("=" * 70)
    
    trends = compute_la_trends(wb_df, measure=measure, min_years=6, weighted=True)
    
    # Merge with classification
    merged = trends.merge(class_df[['la_code', 'supergroup', 'group']], 
                         on='la_code', how='inner')
    
    slopes_dict = dict(zip(merged['la_code'], merged['slope']))
    class_dict = {
        'supergroup': dict(zip(merged['la_code'], merged['supergroup'])),
        'group': dict(zip(merged['la_code'], merged['group']))
    }
    
    # 1. Overall neighbor correlation (as before)
    pairs_overall = []
    for la_code, neighbor_codes in neighbors_dict.items():
        if la_code in slopes_dict and len(neighbor_codes) > 0:
            neighbor_slopes = [slopes_dict[n] for n in neighbor_codes if n in slopes_dict]
            if len(neighbor_slopes) > 0:
                pairs_overall.append((slopes_dict[la_code], np.mean(neighbor_slopes)))
    
    if len(pairs_overall) > 10:
        r_overall, p_overall = stats.pearsonr([p[0] for p in pairs_overall], 
                                               [p[1] for p in pairs_overall])
        print(f"\nOverall neighbor correlation: r = {r_overall:.3f}, p = {p_overall:.4f}")
    
    # 2. WITHIN supergroup neighbor correlation
    print("\nWITHIN-SUPERGROUP neighbor correlations:")
    
    for level in ['supergroup', 'group']:
        print(f"\n  By {level}:")
        
        within_corrs = []
        
        for area_type in merged[level].unique():
            # Get LAs of this type
            type_las = merged[merged[level] == area_type]['la_code'].tolist()
            
            # Get neighbor pairs where BOTH are the same type
            pairs_within = []
            
            for la_code in type_las:
                if la_code in neighbors_dict and la_code in slopes_dict:
                    # Filter to neighbors that are ALSO this type
                    same_type_neighbors = [n for n in neighbors_dict[la_code] 
                                          if n in class_dict[level] 
                                          and class_dict[level][n] == area_type
                                          and n in slopes_dict]
                    
                    if len(same_type_neighbors) > 0:
                        pairs_within.append((
                            slopes_dict[la_code],
                            np.mean([slopes_dict[n] for n in same_type_neighbors])
                        ))
            
            if len(pairs_within) >= 10:  # Need enough pairs for reliable correlation
                r_within, p_within = stats.pearsonr([p[0] for p in pairs_within],
                                                    [p[1] for p in pairs_within])
                
                within_corrs.append({
                    'area_type': area_type,
                    'n_pairs': len(pairs_within),
                    'r': r_within,
                    'p': p_within
                })
        
        if within_corrs:
            within_df = pd.DataFrame(within_corrs).sort_values('r', ascending=False)
            print(within_df.to_string(index=False))

print("\n" + "=" * 70)
print("KEY INTERPRETATION")
print("=" * 70)
print("""
If overall correlation (r=0.2) disappears within area types:
→ It's a CLASSIFICATION ARTIFACT
→ Neighbors are similar because they're the same TYPE
→ No true spillover - just clustering by classification

If correlation PERSISTS within area types (r > 0.15):
→ TRUE SPATIAL SPILLOVER
→ Even controlling for area type, neighbors affect each other
→ Suggests: policy spillovers, labor market integration, or social networks

If some area types show spatial correlation but others don't:
→ Spillovers are CONTEXT-DEPENDENT
→ E.g., might see spillovers in dense urban areas (London boroughs)
→ But not in rural areas (more isolated)

For the paper:
- If artifact: note that classification captures spatial clustering
- If real spillover: recommend spatial clustering in SEs
- If mixed: discuss heterogeneous spillover by area type
""")
