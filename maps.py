#!/usr/bin/env python3
"""
maps.py ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â Choropleth maps of wellbeing trajectories by local authority.

Downloads LA boundary GeoJSON from GitHub (cached locally), merges with
trajectory results, and produces maps.

Usage (standalone):
  python maps.py                              # supergroup, life-satisfaction
  python maps.py --level group --measure anxiety
  python maps.py --england-only

Or import and call from main.py.

Requires: pip install geopandas matplotlib
"""

import argparse
import os
import sys
import json
import warnings
import urllib.request

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd

warnings.filterwarnings('ignore')

from config import DATA_DIR, OUTPUT_DIR, MEASURES, MEASURE_LABELS, SUPERGROUP_NAMES
from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, propagate_classification, remap_scottish_codes, combine_splits
from analysis import compute_la_trends, classify_trajectories

# LA boundary GeoJSON ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ONS Open Geography Portal, LAD May 2023 (UK)
# Super Generalised Clipped boundaries via ArcGIS REST API
GEOJSON_API = (
    "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
    "Local_Authority_Districts_May_2023_UK_BGC_V2/FeatureServer/0/query"
)
GEOJSON_CACHE = os.path.join(DATA_DIR, "la_boundaries_lad23.geojson")


def load_boundaries():
    """Download LAD23 boundaries from ONS ArcGIS API, or load from cache."""
    if os.path.exists(GEOJSON_CACHE):
        print(f"Loading cached boundaries from {GEOJSON_CACHE}...")
        return gpd.read_file(GEOJSON_CACHE)

    print(f"Downloading LAD 2023 boundaries from ONS...")
    try:
        import requests
        params = {
            'where': '1=1',
            'outFields': '*',
            'f': 'geojson',
            'resultOffset': 0,
            'resultRecordCount': 2000,
        }
        all_features = []
        while True:
            resp = requests.get(GEOJSON_API, params=params, timeout=60)
            if not resp.ok:
                break
            data = resp.json()
            features = data.get('features', [])
            if not features:
                break
            all_features.extend(features)
            print(f"  Downloaded {len(all_features)} boundaries...")
            if len(features) < params['resultRecordCount']:
                break
            params['resultOffset'] += len(features)

        if all_features:
            geojson = {'type': 'FeatureCollection', 'features': all_features}
            with open(GEOJSON_CACHE, 'w') as f:
                json.dump(geojson, f)
            print(f"  Cached {len(all_features)} boundaries")
            return gpd.GeoDataFrame.from_features(all_features, crs='EPSG:4326')

    except Exception as e:
        print(f"  API download failed: {e}")

    # Fallback to GitHub
    print(f"  Trying fallback from GitHub...")
    fallback = "https://raw.githubusercontent.com/martinjc/UK-GeoJSON/master/json/administrative/gb/lad.json"
    try:
        urllib.request.urlretrieve(fallback, GEOJSON_CACHE)
        return gpd.read_file(GEOJSON_CACHE)
    except Exception as e:
        print(f"  Fallback failed: {e}")
        print(f"  Download manually from geoportal.statistics.gov.uk")
        print(f"  Search 'LAD May 2023 boundaries', save as {GEOJSON_CACHE}")
        return None


def get_la_code_column(gdf):
    """Find the LA code column in the GeoJSON."""
    # Try common ONS field names first
    for c in ['LAD23CD', 'LAD22CD', 'LAD21CD', 'LAD23CDO', 'lad23cd',
              'CODE', 'code', 'LAD_CODE', 'geo_code']:
        if c in gdf.columns:
            return c
    # Fallback: find column with LA code pattern
    for c in gdf.columns:
        if gdf[c].dropna().astype(str).str.match(r'^[EWSN]\d{2}\d{5}').any():
            return c
    return None


def plot_trajectory_map(gdf, trends_merged, measure, group_col='supergroup',
                        output_dir='output', england_only=False):
    """
    Map showing trajectory classification (improving/stable/deteriorating)
    for each LA, with area type shown by hatching or border colour.
    """
    code_col = get_la_code_column(gdf)
    if code_col is None:
        print("  ERROR: Can't find LA code column in boundary data")
        return

    merged = gdf.merge(trends_merged, left_on=code_col, right_on='la_code',
                        how='left')

    if england_only:
        merged = merged[merged[code_col].str.startswith('E')]

    fig, ax = plt.subplots(1, 1, figsize=(10, 14))

    # Plot background (unmatched LAs in light grey)
    merged.plot(ax=ax, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.2)

    # Overlay trajectory colours
    colours = {'Improving': '#2ca02c', 'Stable': '#ffdd57',
               'Deteriorating': '#d62728'}

    for traj, colour in colours.items():
        subset = merged[merged['trajectory'] == traj]
        if len(subset) > 0:
            subset.plot(ax=ax, color=colour, edgecolor='#666666',
                       linewidth=0.3)

    # Legend
    patches = [mpatches.Patch(color=c, label=t) for t, c in colours.items()]
    patches.append(mpatches.Patch(color='#f0f0f0', label='No data'))
    ax.legend(handles=patches, loc='lower left', fontsize=10,
              framealpha=0.9)

    ax.set_axis_off()
    title = f'{MEASURE_LABELS[measure]}: LA Trajectories 2011-2023'
    if england_only:
        title += ' (England)'
    ax.set_title(title, fontsize=14, fontweight='bold')

    plt.tight_layout()
    suffix = '_england' if england_only else ''
    path = os.path.join(output_dir, f'map_trajectory_{measure}{suffix}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def plot_baseline_map(gdf, trends_merged, measure, output_dir='output',
                      england_only=False):
    """Map showing baseline wellbeing score for each LA."""
    code_col = get_la_code_column(gdf)
    if code_col is None:
        return

    merged = gdf.merge(trends_merged, left_on=code_col, right_on='la_code',
                        how='left')

    if england_only:
        merged = merged[merged[code_col].str.startswith('E')]

    fig, ax = plt.subplots(1, 1, figsize=(10, 14))

    cmap = 'RdYlGn' if measure != 'anxiety' else 'RdYlGn_r'
    merged.plot(ax=ax, column='start_value', cmap=cmap,
                edgecolor='#666666', linewidth=0.2, legend=True,
                legend_kwds={'label': f'Baseline Score (0-10)',
                            'shrink': 0.5},
                missing_kwds={'color': '#f0f0f0'})

    ax.set_axis_off()
    title = f'{MEASURE_LABELS[measure]}: Baseline Score 2011/12'
    if england_only:
        title += ' (England)'
    ax.set_title(title, fontsize=14, fontweight='bold')

    plt.tight_layout()
    suffix = '_england' if england_only else ''
    path = os.path.join(output_dir, f'map_baseline_{measure}{suffix}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def plot_slope_map(gdf, trends_merged, measure, output_dir='output',
                   england_only=False):
    """Map showing trend slope for each LA."""
    code_col = get_la_code_column(gdf)
    if code_col is None:
        return

    merged = gdf.merge(trends_merged, left_on=code_col, right_on='la_code',
                        how='left')

    if england_only:
        merged = merged[merged[code_col].str.startswith('E')]

    fig, ax = plt.subplots(1, 1, figsize=(10, 14))

    # Centre colourmap on zero
    vmax = merged['slope'].abs().quantile(0.95)
    cmap = 'RdYlGn' if measure != 'anxiety' else 'RdYlGn_r'

    merged.plot(ax=ax, column='slope', cmap=cmap, vmin=-vmax, vmax=vmax,
                edgecolor='#666666', linewidth=0.2, legend=True,
                legend_kwds={'label': 'Annual Slope',
                            'shrink': 0.5},
                missing_kwds={'color': '#f0f0f0'})

    ax.set_axis_off()
    title = f'{MEASURE_LABELS[measure]}: Annual Trend 2011-2023'
    if england_only:
        title += ' (England)'
    ax.set_title(title, fontsize=14, fontweight='bold')

    plt.tight_layout()
    suffix = '_england' if england_only else ''
    path = os.path.join(output_dir, f'map_slope_{measure}{suffix}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def plot_classification_map(gdf, class_df, group_col='supergroup',
                            output_dir='output', england_only=False):
    """Map showing area classification for each LA."""
    code_col = get_la_code_column(gdf)
    if code_col is None:
        return

    merged = gdf.merge(class_df, left_on=code_col, right_on='la_code',
                        how='left')

    if england_only:
        merged = merged[merged[code_col].str.startswith('E')]

    fig, ax = plt.subplots(1, 1, figsize=(12, 14))

    groups = sorted(merged[group_col].dropna().unique())
    cmap = plt.cm.Set2 if len(groups) <= 8 else plt.cm.tab20
    colours = {g: cmap(i / max(len(groups) - 1, 1)) for i, g in enumerate(groups)}

    # Background
    merged.plot(ax=ax, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.2)

    for g, color in colours.items():
        subset = merged[merged[group_col] == g]
        if len(subset) > 0:
            subset.plot(ax=ax, color=color, edgecolor='#666666',
                       linewidth=0.2)

    patches = [mpatches.Patch(color=c, label=g) for g, c in colours.items()]
    ax.legend(handles=patches, loc='lower left', fontsize=7,
              framealpha=0.9, ncol=1)

    ax.set_axis_off()
    ax.set_title(f'ONS 2011 Area Classification ({group_col.title()})',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()
    suffix = '_england' if england_only else ''
    path = os.path.join(output_dir, f'map_classification_{group_col}{suffix}.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def generate_all_maps(wb_df, class_df, gdf, measures=None,
                      group_col='supergroup', output_dir='output',
                      england_only=False):
    """Generate all maps for the given measures."""
    if measures is None:
        measures = MEASURES

    os.makedirs(output_dir, exist_ok=True)

    # Classification map
    print("\nClassification map...")
    plot_classification_map(gdf, class_df, group_col=group_col,
                            output_dir=output_dir, england_only=england_only)

    for measure in measures:
        print(f"\n{MEASURE_LABELS[measure]} maps...")

        trends = compute_la_trends(wb_df, measure=measure, min_years=6)
        if len(trends) == 0:
            continue

        classified = classify_trajectories(trends)
        if measure == 'anxiety':
            swap = {'Improving': 'Deteriorating', 'Deteriorating': 'Improving'}
            classified['trajectory'] = classified['trajectory'].map(
                lambda x: swap.get(x, x))

        # Merge with classification
        merged = classified.merge(class_df[['la_code', group_col]],
                                   on='la_code', how='left')

        plot_trajectory_map(gdf, merged, measure, group_col=group_col,
                           output_dir=output_dir, england_only=england_only)
        plot_baseline_map(gdf, merged, measure, output_dir=output_dir,
                         england_only=england_only)
        plot_slope_map(gdf, merged, measure, output_dir=output_dir,
                      england_only=england_only)


def combine_boundary_splits(gdf, code_col):
    """
    Combine split authority boundaries into single polygons for combined codes.
    
    Dissolves geometries for:
    - E06000061 + E06000062 → NORTHANTS_COMBINED
    - E06000058 + E06000059 → DORSET_COMBINED  
    - E06000063 + E06000064 → CUMBRIA_COMBINED
    """
    from boundaries import BOUNDARY_SPLITS
    
    print("\nCombining split authority boundaries...")
    gdf = gdf.copy()
    additions = []
    
    for combined_code, info in BOUNDARY_SPLITS.items():
        split_parts = info['split_parts']
        name = info['name']
        
        # Find the split parts in the boundary file
        parts_geom = gdf[gdf[code_col].isin(split_parts)]
        
        if len(parts_geom) == 0:
            continue
        
        # Dissolve geometries into one polygon
        dissolved = parts_geom.dissolve()
        dissolved[code_col] = combined_code
        
        # Reset index to get it as a regular row
        dissolved = dissolved.reset_index(drop=True)
        
        additions.append(dissolved)
        
        print(f"  {name}: dissolved {len(parts_geom)} parts → {combined_code}")
    
    if additions:
        # Remove original split parts
        all_splits = []
        for info in BOUNDARY_SPLITS.values():
            all_splits.extend(info['split_parts'])
        
        gdf = gdf[~gdf[code_col].isin(all_splits)]
        
        # Add combined geometries
        combined_gdf = pd.concat([gdf] + additions, ignore_index=True)
        
        print(f"  Boundary total: {len(gdf)} + {len(additions)} = {len(combined_gdf)} LAs")
        return combined_gdf
    
    return gdf


def main():
    parser = argparse.ArgumentParser(description='Generate wellbeing maps')
    parser.add_argument('--level', choices=['supergroup', 'group', 'subgroup'],
                        default='supergroup')
    parser.add_argument('--measure', choices=MEASURES + ['all'], default='all')
    parser.add_argument('--england-only', action='store_true')
    parser.add_argument('--no-combine-splits', action='store_true',
                        help='Keep split authorities separate (default: combine to county footprints)')
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    if not check_data_files():
        return

    # Load data
    wb_df = load_wellbeing_data()
    wb_df = harmonise_boundaries(wb_df)
    class_df = load_area_classification()
    class_df = propagate_classification(class_df)

    # Remap Scottish codes to match LAD23 boundaries
    wb_df = remap_scottish_codes(wb_df)
    class_df = remap_scottish_codes(class_df)

    # Combine county splits by default (maintains historic geography)
    # Use --no-combine-splits to keep ONS published split codes
    if not args.no_combine_splits:
        wb_df = combine_splits(wb_df)
        class_df = combine_splits(class_df)

    if args.england_only:
        wb_df = wb_df[wb_df['la_code'].str.startswith('E')]
        class_df = class_df[class_df['la_code'].str.startswith('E')]

    # Load boundaries
    gdf = load_boundaries()
    if gdf is None:
        return
    
    # Combine split authority boundaries to match data (if combining splits)
    if not args.no_combine_splits:
        code_col = get_la_code_column(gdf)
        if code_col:
            gdf = combine_boundary_splits(gdf, code_col)

    measures = MEASURES if args.measure == 'all' else [args.measure]
    dir_name = f"{args.level}_england" if args.england_only else args.level
    out_dir = os.path.join(OUTPUT_DIR, dir_name, 'maps')

    generate_all_maps(wb_df, class_df, gdf, measures=measures,
                      group_col=args.level, output_dir=out_dir,
                      england_only=args.england_only)

    print(f"\nDone. Maps in {out_dir}/")


if __name__ == '__main__':
    main()
