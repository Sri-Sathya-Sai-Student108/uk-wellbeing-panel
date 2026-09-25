"""
Analyze correlations between the four wellbeing measures.

Part 1: Temporal - do slopes correlate across measures at LA level?
Part 2: Spatial - do neighboring LAs have similar trajectories?
"""

from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, remap_scottish_codes, combine_splits, propagate_classification
from analysis import compute_la_trends
from config import MEASURES, MEASURE_LABELS
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import os

print("=" * 70)
print("WELLBEING MEASURE CORRELATIONS")
print("=" * 70)

if not check_data_files():
    exit()

# Load data
wb_df = load_wellbeing_data()
wb_df = harmonise_boundaries(wb_df)
wb_df = remap_scottish_codes(wb_df)
wb_df = combine_splits(wb_df)

# Compute slopes for all 4 measures
slopes_all = {}

for measure in MEASURES:
    trends = compute_la_trends(wb_df, measure=measure, min_years=6, weighted=True)
    slopes_all[measure] = trends.set_index('la_code')[['slope', 'p_value']]

slopes_df = pd.DataFrame({m: slopes_all[m]['slope'] for m in MEASURES})

print(f"\nComputed slopes for {len(slopes_df)} LAs across 4 measures")

# Correlation matrix
print("\n" + "=" * 70)
print("SLOPE CORRELATION MATRIX")
print("=" * 70)

corr = slopes_df.corr()
print(corr.round(3))

print("\nWith significance tests:")
for i, m1 in enumerate(MEASURES):
    for j, m2 in enumerate(MEASURES):
        if i < j:
            valid = slopes_df[[m1, m2]].dropna()
            if len(valid) > 10:
                r, p = stats.pearsonr(valid[m1], valid[m2])
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
                print(f"  {MEASURE_LABELS[m1]:20s} × {MEASURE_LABELS[m2]:20s}: r={r:6.3f}, p={p:.4f} {sig}")

# Save correlation heatmap
try:
    import seaborn as sns
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt='.3f', cmap='RdBu_r', center=0, vmin=-1, vmax=1,
                xticklabels=[MEASURE_LABELS[m] for m in MEASURES],
                yticklabels=[MEASURE_LABELS[m] for m in MEASURES])
    plt.title('Trajectory Slope Correlations Across Measures')
    plt.tight_layout()
    os.makedirs('output', exist_ok=True)
    plt.savefig('output/slope_correlation_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\nSaved: output/slope_correlation_heatmap.png")
except ImportError:
    print("\nseaborn not available for heatmap visualization")

print("\n" + "=" * 70)
print("INTERPRETATION")
print("=" * 70)
print("""
High correlation (r > 0.5):
→ Measures track together - common drivers

Low correlation (r < 0.3):
→ Measures are independent - different drivers
→ Supports multi-dimensional wellbeing framework

Negative correlation (r < 0):
→ Trade-offs or inverse relationships
→ E.g., if life-sat improves but anxiety worsens
""")
