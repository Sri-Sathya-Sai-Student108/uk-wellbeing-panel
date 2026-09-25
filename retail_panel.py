#!/usr/bin/env python3
"""
retail_panel.py - Build retail store counts panel from Geolytix snapshots.

Reads annual Geolytix retail point snapshots, spatially joins stores to
local authority boundaries, and counts incumbent vs discounter stores
per LAD per year. Produces separate outputs for England and Scotland
with country-appropriate retailer definitions.

Outputs:
  data/intermediate/retail_data_england.csv
  data/intermediate/retail_data_scotland.csv

    la_code, la_name, year, tot, tot_new, tot_old

    tot     = total major retailers
    tot_new = discounters (Aldi, Lidl) - the expanding chains
    tot_old = incumbents - the established chains

Retailer definitions
--------------------
England incumbents:
    Tesco, Asda, Sainsburys, Morrisons, Iceland, Marks and Spencer, Waitrose

Scotland incumbents (adds Co-op, removes Waitrose):
    Tesco, Asda, Sainsburys, Morrisons, Iceland, Marks and Spencer,
    all Co-operative societies (31.8% of Scottish major retail footprint),
    Scottish Midland Co-operative (Scotmid)
    Waitrose excluded - only 6 stores in Scotland (negligible)

Excluded fascias (petrol stations / motorway services - not employment sites):
    Asda PFS, Marks and Spencer BP, Marks and Spencer MSA,
    Tesco Express Esso, Waitrose MSA, Little Waitrose Shell,
    The Co-operative Food PFS

Note on spatial join:
    R's original Stata code uses a postcode -> LSOA -> LAD lookup table.
    That file exceeds upload limits, so we use a spatial join on store
    lat/lon coordinates against LAD23 boundaries instead. Results are
    equivalent for well-geocoded stores. Methodology deviation documented
    in paper Methods section.

Note on file selection:
    Geolytix publishes multiple snapshot files per year. We take the
    latest version per calendar year. When two files share the same
    year-month, the higher version number wins.

Usage:
  python retail_panel.py                        # both England and Scotland
  python retail_panel.py --country england      # England only
  python retail_panel.py --country scotland     # Scotland only
  python retail_panel.py --geolytix-dir data/geolytix
  python retail_panel.py --years 2016 2020 2021 2022 2023
"""

import argparse
import os
import re
import sys
import warnings

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point

warnings.filterwarnings('ignore')

from config import DATA_DIR

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
GEOLYTIX_DIR     = os.path.join(DATA_DIR, 'geolytix')
INTERMEDIATE_DIR = os.path.join(DATA_DIR, 'intermediate')
BOUNDARY_CACHE   = os.path.join(DATA_DIR, 'la_boundaries_lad23.geojson')

OUTPUT_ENGLAND  = os.path.join(INTERMEDIATE_DIR, 'retail_data_england.csv')
OUTPUT_SCOTLAND = os.path.join(INTERMEDIATE_DIR, 'retail_data_scotland.csv')

YEAR_MIN = 2016
YEAR_MAX = 2023

# ---------------------------------------------------------------------------
# Retailer definitions
# ---------------------------------------------------------------------------

DISCOUNTERS = {'Aldi', 'Lidl'}

INCUMBENTS_ENGLAND = {
    'Tesco', 'Asda', 'Sainsburys', 'Morrisons',
    'Iceland', 'Marks and Spencer', 'Waitrose',
}

# Co-op has 31.8% of Scottish major retail footprint vs 22% in England.
# Waitrose has only 6 stores in Scotland — excluded as negligible.
INCUMBENTS_SCOTLAND = {
    'Tesco', 'Asda', 'Sainsburys', 'Morrisons',
    'Iceland', 'Marks and Spencer',
    'The Co-operative Group',
    'Scottish Midland Co-operative',
    'The Southern Co-operative',
    'Central England Co-operative',
    'Midcounties Co-operative',
    'East of England Co-operative',
    'Lincolnshire Co-operative',
}

EXCLUDE_FASCIAS = {
    'Asda PFS',
    'Marks and Spencer BP',
    'Marks and Spencer MSA',
    'Tesco Express Esso',
    'Waitrose MSA',
    'Little Waitrose Shell',
    'The Co-operative Food PFS',
}


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def parse_geolytix_filename(filename):
    """
    Extract version and date from Geolytix filename.
    Expected format: geolytix_retailpoints_vN_YYYYMM.csv
    Returns (version, year, month) or None.
    """
    m = re.match(r'geolytix_retailpoints_v(\d+)_(\d{4})(\d{2})\.csv',
                 filename, re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def find_latest_file_per_year(geolytix_dir, year_min, year_max):
    """
    Scan directory for Geolytix snapshot files and return the latest
    file per calendar year within [year_min, year_max].

    When two files share the same year-month, highest version wins.

    Returns dict: {year: filepath}
    """
    candidates = {}
    for fname in os.listdir(geolytix_dir):
        parsed = parse_geolytix_filename(fname)
        if parsed is None:
            continue
        version, year, month = parsed
        if not (year_min <= year <= year_max):
            continue
        filepath = os.path.join(geolytix_dir, fname)
        if year not in candidates:
            candidates[year] = (version, month, filepath)
        else:
            prev_ver, prev_month, _ = candidates[year]
            if (month, version) > (prev_month, prev_ver):
                candidates[year] = (version, month, filepath)

    return {year: fp for year, (_, _, fp) in sorted(candidates.items())}


# ---------------------------------------------------------------------------
# Boundary loading
# ---------------------------------------------------------------------------

def load_boundaries(country):
    """
    Load LAD23 boundaries filtered to England (E codes) or Scotland (S codes).
    Downloads and caches from ONS ArcGIS API if not already cached.
    """
    prefix = 'E' if country == 'england' else 'S'

    if os.path.exists(BOUNDARY_CACHE):
        gdf = gpd.read_file(BOUNDARY_CACHE)
    else:
        print(f"  Downloading LAD23 boundaries from ONS ArcGIS API...")
        try:
            import requests, json
            api = (
                "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
                "Local_Authority_Districts_May_2023_UK_BGC_V2/FeatureServer/0/query"
            )
            params = {'where': '1=1', 'outFields': '*', 'f': 'geojson',
                      'resultOffset': 0, 'resultRecordCount': 2000}
            features = []
            while True:
                resp = requests.get(api, params=params, timeout=60)
                batch = resp.json().get('features', [])
                if not batch:
                    break
                features.extend(batch)
                if len(batch) < params['resultRecordCount']:
                    break
                params['resultOffset'] += len(batch)
            with open(BOUNDARY_CACHE, 'w') as f:
                json.dump({'type': 'FeatureCollection', 'features': features}, f)
            gdf = gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')
            print(f"  Downloaded and cached {len(gdf)} boundaries")
        except Exception as e:
            print(f"  ERROR: {e}")
            sys.exit(1)

    code_col = next((c for c in ['LAD23CD','LAD22CD','LAD21CD','lad23cd','CODE']
                     if c in gdf.columns), None)
    name_col = next((c for c in ['LAD23NM','LAD22NM','LAD21NM','lad23nm','NAME']
                     if c in gdf.columns), None)

    if code_col is None:
        print("  ERROR: Cannot find LAD code column in boundary file")
        sys.exit(1)

    filtered = gdf[gdf[code_col].str.startswith(prefix, na=False)].copy()
    filtered = filtered.rename(columns={code_col: 'la_code'})
    if name_col:
        filtered = filtered.rename(columns={name_col: 'la_name'})
    else:
        filtered['la_name'] = filtered['la_code']

    filtered = filtered.to_crs('EPSG:4326')
    label = 'English LADs' if country == 'england' else 'Scottish council areas'
    print(f"  {len(filtered)} {label} loaded")
    return filtered[['la_code', 'la_name', 'geometry']]


# ---------------------------------------------------------------------------
# Process one snapshot file
# ---------------------------------------------------------------------------

def process_snapshot(filepath, year, boundaries_gdf, all_retailers,
                     discounters, incumbents):
    """
    Load one Geolytix snapshot, filter to relevant retailers,
    spatially join to LAD boundaries, and return counts per LAD.

    Returns DataFrame: la_code, la_name, year, tot, tot_new, tot_old
    """
    print(f"  Reading {os.path.basename(filepath)}...", end=' ', flush=True)
    df = pd.read_csv(filepath, low_memory=False)
    df.columns = df.columns.str.lower().str.strip()

    rename = {}
    for col in df.columns:
        if col in ('long_wgs', 'longitude', 'long'):
            rename[col] = 'lon'
        elif col in ('lat_wgs', 'latitude', 'lat'):
            rename[col] = 'lat'
    df = df.rename(columns=rename)

    required = {'retailer', 'fascia', 'lon', 'lat'}
    if required - set(df.columns):
        print(f"WARNING: missing columns {required - set(df.columns)}")
        return None

    # Filter retailers and exclude petrol/MSA fascias
    df = df[df['retailer'].isin(all_retailers)].copy()
    df = df[~df['fascia'].isin(EXCLUDE_FASCIAS)].copy()

    if len(df) == 0:
        print("WARNING: no matching retailers")
        return None

    # Drop invalid coordinates
    n_before = len(df)
    df = df.dropna(subset=['lon', 'lat'])
    df = df[(df['lon'].between(-8, 2)) & (df['lat'].between(49, 61))]
    n_dropped = n_before - len(df)

    # Classify
    df['is_new'] = df['retailer'].isin(discounters).astype(int)
    df['is_old'] = df['retailer'].isin(incumbents).astype(int)
    df['obs']    = 1

    # Spatial join
    store_gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(lon, lat) for lon, lat in zip(df['lon'], df['lat'])],
        crs='EPSG:4326'
    )
    joined = gpd.sjoin(
        store_gdf[['obs', 'is_new', 'is_old', 'geometry']],
        boundaries_gdf[['la_code', 'la_name', 'geometry']],
        how='inner', predicate='within'
    )

    result = joined.groupby(['la_code', 'la_name']).agg(
        tot     = ('obs',    'sum'),
        tot_new = ('is_new', 'sum'),
        tot_old = ('is_old', 'sum'),
    ).reset_index()

    result['year'] = year
    n_unmatched = len(store_gdf) - len(joined)
    print(f"{result['tot'].sum():.0f} stores "
          f"({result['tot_new'].sum():.0f} disc, "
          f"{result['tot_old'].sum():.0f} inc)"
          + (f", {n_unmatched} outside boundary" if n_unmatched > 0 else ""))
    return result


# ---------------------------------------------------------------------------
# Build one country panel
# ---------------------------------------------------------------------------

def build_retail_panel(country, geolytix_dir=GEOLYTIX_DIR,
                        year_min=YEAR_MIN, year_max=YEAR_MAX,
                        years=None):
    """
    Build retail panel for one country.

    country: 'england' or 'scotland'
    Returns DataFrame and saves CSV.
    """
    assert country in ('england', 'scotland')
    output_file = OUTPUT_ENGLAND if country == 'england' else OUTPUT_SCOTLAND

    label = country.title()
    incumbents = INCUMBENTS_ENGLAND if country == 'england' else INCUMBENTS_SCOTLAND
    all_retailers = DISCOUNTERS | incumbents

    print(f"\n{'='*60}")
    print(f"RETAIL PANEL — {label.upper()}")
    print(f"Discounters:  {sorted(DISCOUNTERS)}")
    print(f"Incumbents:   {len(incumbents)} chains")
    print(f"Period:       {year_min}-{year_max}")
    print(f"{'='*60}")

    if not os.path.isdir(geolytix_dir):
        print(f"\nERROR: Geolytix directory not found: {geolytix_dir}")
        print(f"Copy v1-v36 Geolytix CSV files there.")
        sys.exit(1)

    # Discover files
    print("\nDiscovering Geolytix snapshot files...")
    file_map = find_latest_file_per_year(geolytix_dir, year_min, year_max)
    if not file_map:
        print(f"ERROR: No Geolytix files found in {geolytix_dir}")
        sys.exit(1)

    print(f"  Found {len(file_map)} annual snapshots:")
    for year, fp in sorted(file_map.items()):
        print(f"    {year}: {os.path.basename(fp)}")

    if years:
        file_map = {y: fp for y, fp in file_map.items() if y in years}

    # Load boundaries
    print(f"\nLoading {label} boundaries...")
    boundaries = load_boundaries(country)

    # Process each year
    print("\nProcessing snapshots:")
    panels = []
    for year, filepath in sorted(file_map.items()):
        print(f"  {year}: ", end='')
        result = process_snapshot(filepath, year, boundaries,
                                  all_retailers, DISCOUNTERS, incumbents)
        if result is not None:
            panels.append(result)

    if not panels:
        print("\nERROR: No data produced")
        return None

    panel = pd.concat(panels, ignore_index=True)
    panel = panel.sort_values(['la_code', 'year']).reset_index(drop=True)

    # Summary
    n_years = panel['year'].nunique()
    n_las   = panel['la_code'].nunique()
    print(f"\nPanel summary:")
    print(f"  LADs:         {n_las}")
    print(f"  Years:        {sorted(panel['year'].unique())}")
    print(f"  Observations: {len(panel)}")
    if n_las * n_years == len(panel):
        print(f"  Balance:      BALANCED ({n_years} x {n_las})")
    else:
        print(f"  Balance:      UNBALANCED")

    print(f"\n  Store counts by year:")
    by_year = panel.groupby('year')[['tot','tot_new','tot_old']].sum()
    by_year.columns = ['Total','Discounters','Incumbents']
    print(by_year.to_string())

    # Check for LADs with no stores
    all_lads = set(boundaries['la_code'])
    missing  = all_lads - set(panel['la_code'])
    if missing:
        names = boundaries[boundaries['la_code'].isin(missing)]['la_name'].tolist()
        print(f"\n  LADs with no stores: {sorted(names)}")

    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    panel.to_csv(output_file, index=False)
    print(f"\n  Saved: {output_file}")
    return panel


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Build retail panel from Geolytix snapshots')
    parser.add_argument('--country', choices=['england','scotland','both'],
                        default='both',
                        help='Which country panel to build (default: both)')
    parser.add_argument('--geolytix-dir', default=GEOLYTIX_DIR)
    parser.add_argument('--years', nargs='+', type=int, default=None)
    parser.add_argument('--year-min', type=int, default=YEAR_MIN)
    parser.add_argument('--year-max', type=int, default=YEAR_MAX)
    args = parser.parse_args()

    years = set(args.years) if args.years else None

    if args.country in ('england', 'both'):
        build_retail_panel('england', args.geolytix_dir,
                           args.year_min, args.year_max, years)

    if args.country in ('scotland', 'both'):
        build_retail_panel('scotland', args.geolytix_dir,
                           args.year_min, args.year_max, years)

    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
