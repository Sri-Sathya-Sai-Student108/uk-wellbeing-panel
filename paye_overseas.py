#!/usr/bin/env python3
"""
paye_overseas.py - Download and parse HMRC PAYE overseas worker share
in health and social care, by region, 2016-2023.

Source:
  HMRC Pay As You Earn Real Time Information (RTI) data linked to
  Migrant Worker Scan (MWS).
  Published: "UK payrolled employments by nationality, region, industry,
  age and sex, from July 2014 to December 2024"
  URL: https://www.gov.uk/government/statistics/uk-payrolled-employments-
       by-nationality-region-industry-age-and-sex-from-july-2014-to-december-2024

What this produces:
  Overseas worker share in health and social work (SIC Q) by region,
  computed as annual mean of monthly (EU + non-EU) / total.

Geography:
  Regions: 9 English regions + Scotland + Wales + Northern Ireland
  Each LA in the panel inherits its region's overseas share value.
  Scotland is treated as a single region (one value for all 32 council areas).
  England: each LA is assigned its containing region's value.

Note on data interpretation:
  The paper (Radakrishnan et al.) uses overseas worker share as a
  predetermined heterogeneity variable, not a time-varying covariate.
  It calculates each region's 2020-2023 AVERAGE share and classifies
  regions as high/low overseas worker availability using the median split.
  We produce annual values here so users can choose how to use them.

Outputs:
  data/intermediate/paye_overseas_regional.csv
    region, year, hsw_total, hsw_uk, hsw_eu, hsw_noneu, overseas_share

  data/intermediate/paye_overseas_la.csv
    la_code, la_name, year, region, overseas_share
    (LA panel: each LA assigned its region's value)

Usage:
  python paye_overseas.py
  python make.py paye
"""

import os
import sys
import time
import warnings

import pandas as pd
import numpy as np
import requests

warnings.filterwarnings('ignore')

from config import DATA_DIR

INTERMEDIATE_DIR = os.path.join(DATA_DIR, 'intermediate')
NOMIS_DIR        = os.path.join(DATA_DIR, 'nomis')

PAYE_URL   = (
    'https://assets.publishing.service.gov.uk/media/67d048d70c485ba007779fb1/'
    'Payrolled_employments_in_the_UK_by_nationality__region_and_industry__'
    'from_July_2014_to_December_2024.ods'
)
PAYE_CACHE_ODS     = os.path.join(NOMIS_DIR, 'paye_nationality_region_industry.ods')
REGIONAL_CACHE_CSV = os.path.join(INTERMEDIATE_DIR, 'paye_overseas_regional.csv')
LA_CACHE_CSV       = os.path.join(INTERMEDIATE_DIR, 'paye_overseas_la.csv')

YEAR_MIN = 2016
YEAR_MAX = 2023

# Sheet number -> region name mapping (from ODS contents sheet)
SHEET_REGIONS = {
    '6':  'North East',
    '7':  'North West',
    '8':  'Yorkshire and the Humber',
    '9':  'East Midlands',
    '10': 'West Midlands',
    '11': 'East of England',
    '12': 'London',
    '13': 'South East',
    '14': 'South West',
    '15': 'Scotland',
    '16': 'Wales',
    '17': 'Northern Ireland',
}

# ONS region codes for joining to LA boundary data
REGION_CODES = {
    'North East':              'E12000001',
    'North West':              'E12000002',
    'Yorkshire and the Humber':'E12000003',
    'East Midlands':           'E12000004',
    'West Midlands':           'E12000005',
    'East of England':         'E12000006',
    'London':                  'E12000007',
    'South East':              'E12000008',
    'South West':              'E12000009',
    'Scotland':                'S92000003',
    'Wales':                   'W92000004',
    'Northern Ireland':        'N92000002',
}

# Health and social work column names in the ODS
HSW_TOTAL  = 'Total employment counts in Health and social work'
HSW_UK     = 'Total UK nationals employment counts in Health and social work'
HSW_EU     = 'Total EU nationals employment counts in Health and social work'
HSW_NONEU  = 'Total non-EU nationals employment counts in Health and social work'


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_paye_ods(force_refresh=False):
    """Download the HMRC PAYE ODS file and cache locally."""
    os.makedirs(NOMIS_DIR, exist_ok=True)

    if os.path.exists(PAYE_CACHE_ODS) and not force_refresh:
        print(f"  Using cached ODS: {PAYE_CACHE_ODS}")
        return PAYE_CACHE_ODS

    print(f"  Downloading HMRC PAYE data (~1.2 MB)...")
    try:
        r = requests.get(PAYE_URL, timeout=120)
        r.raise_for_status()
        with open(PAYE_CACHE_ODS, 'wb') as f:
            f.write(r.content)
        print(f"  Saved: {PAYE_CACHE_ODS} ({len(r.content)/1024:.0f} KB)")
        return PAYE_CACHE_ODS
    except Exception as e:
        print(f"  ERROR downloading PAYE data: {e}")
        print(f"  Download manually from:")
        print(f"  {PAYE_URL}")
        print(f"  Save as: {PAYE_CACHE_ODS}")
        return None


# ---------------------------------------------------------------------------
# Parse one regional sheet
# ---------------------------------------------------------------------------

def parse_region_sheet(ods_path, sheet, region_name, year_min, year_max):
    """
    Parse one regional sheet from the PAYE ODS file.

    Returns DataFrame: region, year, month, hsw_total, hsw_uk,
                       hsw_eu, hsw_noneu
    """
    df = pd.read_excel(ods_path, sheet_name=sheet, engine='odf', header=None)

    # Detect header row dynamically (varies by sheet - usually row 3, but
    # some sheets have it at row 2)
    header_row = None
    for i in range(min(8, len(df))):
        row_vals = [str(v).lower() for v in df.iloc[i].tolist()]
        if any('total employment' in v for v in row_vals):
            header_row = i
            break

    if header_row is None:
        print(f"    WARNING: Could not find header row in sheet {sheet}")
        return None

    header = df.iloc[header_row].tolist()
    data   = df.iloc[header_row + 1:].copy()
    data.columns = header

    # Rename date column
    data = data.rename(columns={data.columns[0]: 'date'})
    data['date'] = pd.to_datetime(data['date'], errors='coerce')
    data = data.dropna(subset=['date'])

    # Filter to study years
    data['year']  = data['date'].dt.year
    data['month'] = data['date'].dt.month
    data = data[(data['year'] >= year_min) & (data['year'] <= year_max)]

    if len(data) == 0:
        print(f"    WARNING: No data for {region_name} in {year_min}-{year_max}")
        return None

    # Extract health & social work columns, coerce to numeric
    for col in [HSW_TOTAL, HSW_UK, HSW_EU, HSW_NONEU]:
        data[col] = pd.to_numeric(data[col], errors='coerce')

    result = data[['date', 'year', 'month',
                   HSW_TOTAL, HSW_UK, HSW_EU, HSW_NONEU]].copy()
    result = result.rename(columns={
        HSW_TOTAL: 'hsw_total',
        HSW_UK:    'hsw_uk',
        HSW_EU:    'hsw_eu',
        HSW_NONEU: 'hsw_noneu',
    })
    result['region'] = region_name
    return result


# ---------------------------------------------------------------------------
# Build regional panel
# ---------------------------------------------------------------------------

def build_regional_panel(ods_path, year_min=YEAR_MIN, year_max=YEAR_MAX):
    """
    Parse all regional sheets and compute annual mean overseas share
    in health and social work.

    Returns DataFrame: region, year, hsw_total, hsw_uk, hsw_eu,
                       hsw_noneu, overseas_share
    """
    print(f"\n  Parsing {len(SHEET_REGIONS)} regional sheets...")
    all_monthly = []

    for sheet, region in SHEET_REGIONS.items():
        print(f"    {region}...", end=' ', flush=True)
        df = parse_region_sheet(ods_path, sheet, region, year_min, year_max)
        if df is not None:
            all_monthly.append(df)
            print(f"OK ({len(df)} months)")
        else:
            print("FAILED")

    monthly = pd.concat(all_monthly, ignore_index=True)

    # Annual mean across all months
    annual = (monthly
              .groupby(['region', 'year'])
              .agg(
                  hsw_total  = ('hsw_total',  'mean'),
                  hsw_uk     = ('hsw_uk',     'mean'),
                  hsw_eu     = ('hsw_eu',     'mean'),
                  hsw_noneu  = ('hsw_noneu',  'mean'),
                  n_months   = ('month',       'count'),
              )
              .reset_index())

    # Flag incomplete years
    incomplete = annual[annual['n_months'] < 12]
    if len(incomplete) > 0:
        print(f"\n  NOTE: {len(incomplete)} region-years have <12 months:")
        for _, row in incomplete.iterrows():
            print(f"    {row['region']} {row['year']}: {row['n_months']} months")

    # Overseas share = (EU + non-EU) / total
    annual['overseas_share'] = (
        (annual['hsw_eu'] + annual['hsw_noneu']) / annual['hsw_total']
    ).round(4)

    # Add region code
    annual['region_code'] = annual['region'].map(REGION_CODES)

    # Round counts
    for col in ['hsw_total', 'hsw_uk', 'hsw_eu', 'hsw_noneu']:
        annual[col] = annual[col].round(0)

    print(f"\n  Regional overseas share in health & social work:")
    summary = (annual[annual['year'].between(2020, 2023)]
               .groupby('region')['overseas_share']
               .mean()
               .sort_values(ascending=False)
               .round(3))
    for region, share in summary.items():
        bar = '#' * int(share * 100)
        print(f"    {region:30s}: {share:.3f} {bar}")

    return annual


# ---------------------------------------------------------------------------
# Assign to LAs
# ---------------------------------------------------------------------------

def assign_to_las(regional_df):
    """
    Assign regional overseas share to each LA in the panel.

    Uses LA-to-region lookup from the ONS boundary file.
    Each LA inherits its containing region's overseas share.

    Returns DataFrame: la_code, la_name, year, region, overseas_share
    """
    print("\n  Assigning regional values to LAs...")

    # Build LA -> region lookup from boundary file
    boundary_cache = os.path.join(DATA_DIR, 'la_boundaries_lad23.geojson')
    if not os.path.exists(boundary_cache):
        print("  WARNING: Boundary file not found - run maps.py first")
        return None

    try:
        import geopandas as gpd
        gdf = gpd.read_file(boundary_cache)

        # Find code and region columns
        code_col = next((c for c in ['LAD23CD','LAD22CD','lad23cd','CODE']
                         if c in gdf.columns), None)
        name_col = next((c for c in ['LAD23NM','LAD22NM','lad23nm','NAME']
                         if c in gdf.columns), None)

        if code_col is None:
            print("  ERROR: Cannot find LA code column in boundary file")
            return None

    except Exception as e:
        print(f"  ERROR loading boundary file: {e}")
        return None

    # Assign region from LA code prefix
    # E = England (need to look up specific region)
    # S = Scotland, W = Wales, N = Northern Ireland
    la_codes  = gdf[code_col].tolist()
    la_names  = gdf[name_col].tolist() if name_col else la_codes

    la_region = []
    for code, name in zip(la_codes, la_names):
        if code.startswith('S'):
            la_region.append((code, name, 'Scotland'))
        elif code.startswith('W'):
            la_region.append((code, name, 'Wales'))
        elif code.startswith('N'):
            la_region.append((code, name, 'Northern Ireland'))
        elif code.startswith('E'):
            # Derive English region from LA code
            region = _la_to_english_region(code)
            la_region.append((code, name, region))

    la_lookup = pd.DataFrame(la_region,
                              columns=['la_code', 'la_name', 'region'])

    # Merge with regional overseas share
    result = la_lookup.merge(
        regional_df[['region', 'year', 'overseas_share']],
        on='region', how='left'
    )

    # Flag unmatched
    unmatched = result[result['overseas_share'].isna()]['la_code'].unique()
    if len(unmatched) > 0:
        print(f"  WARNING: {len(unmatched)} LAs unmatched to region")

    print(f"  {result['la_code'].nunique()} LAs assigned regional values")
    return result


def _la_to_english_region(la_code):
    """Map English LA code to region name using cached lookup."""
    if not hasattr(_la_to_english_region, '_lookup'):
        lookup_path = os.path.join(DATA_DIR, 'la_to_region_lookup.csv')
        if os.path.exists(lookup_path):
            lu = pd.read_csv(lookup_path).set_index('la_code')['region'].to_dict()
        else:
            lu = {}
        _la_to_english_region._lookup = lu
    return _la_to_english_region._lookup.get(la_code, 'Unknown')


# ---------------------------------------------------------------------------
# Build region lookup from ONS Open Geography Portal
# ---------------------------------------------------------------------------

def build_la_region_lookup():
    """
    Download LA-to-region lookup for England from ONS Open Geography Portal.
    Scotland, Wales and NI are handled separately by code prefix.
    Saves to data/la_to_region_lookup.csv.
    Returns DataFrame: la_code, la_name, region_code, region
    """
    lookup_path = os.path.join(DATA_DIR, 'la_to_region_lookup.csv')
    if os.path.exists(lookup_path):
        df = pd.read_csv(lookup_path)
        print(f"  Using cached LA-region lookup ({len(df)} English LAs)")
        return df

    print("  Downloading LA-to-region lookup from ONS...")
    url = (
        'https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/'
        'LAD23_RGN23_EN_LU/FeatureServer/0/query'
        '?where=1%3D1&outFields=LAD23CD,LAD23NM,RGN23CD,RGN23NM'
        '&f=json&resultRecordCount=400'
    )
    try:
        r = requests.get(url, timeout=30)
        features = r.json().get('features', [])
        rows = [f['attributes'] for f in features]
        df = pd.DataFrame(rows)
        df = df.rename(columns={
            'LAD23CD': 'la_code',
            'LAD23NM': 'la_name',
            'RGN23CD': 'region_code',
            'RGN23NM': 'region',
        })
        # Normalise region name to match PAYE sheet names
        df['region'] = df['region'].replace({
            'East': 'East of England',
            'Yorkshire and The Humber': 'Yorkshire and the Humber',
        })
        df.to_csv(lookup_path, index=False)
        print(f"  Saved: {lookup_path} ({len(df)} English LAs)")
        return df
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def download_paye_overseas(year_min=YEAR_MIN, year_max=YEAR_MAX,
                            force_refresh=False):
    """
    Download and process HMRC PAYE overseas worker share data.

    Returns (regional_df, la_df)
    """
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    os.makedirs(NOMIS_DIR, exist_ok=True)

    # Check cache
    if (os.path.exists(REGIONAL_CACHE_CSV) and
            os.path.exists(LA_CACHE_CSV) and
            not force_refresh):
        print(f"  Loading cached PAYE data...")
        regional = pd.read_csv(REGIONAL_CACHE_CSV)
        la_df    = pd.read_csv(LA_CACHE_CSV)
        print(f"  Regional: {len(regional)} obs, "
              f"{regional['region'].nunique()} regions")
        print(f"  LA-level: {len(la_df)} obs, "
              f"{la_df['la_code'].nunique()} LAs")
        return regional, la_df

    print("=" * 60)
    print("HMRC PAYE OVERSEAS WORKER SHARE")
    print("Health and social work, by region, annual mean")
    print("=" * 60)

    # Download ODS
    print("\n1. Downloading ODS file...")
    ods_path = download_paye_ods(force_refresh)
    if ods_path is None:
        return None, None

    # Parse regional data
    print("\n2. Parsing regional data...")
    regional = build_regional_panel(ods_path, year_min, year_max)

    # Save regional
    regional.to_csv(REGIONAL_CACHE_CSV, index=False)
    print(f"\n  Saved: {REGIONAL_CACHE_CSV}")

    # Build LA-to-region lookup if needed
    print("\n3. Building LA-to-region lookup...")
    build_la_region_lookup()

    # Assign to LAs
    print("\n4. Assigning to LAs...")
    la_df = assign_to_las(regional)

    if la_df is not None:
        la_df.to_csv(LA_CACHE_CSV, index=False)
        print(f"  Saved: {LA_CACHE_CSV}")
    else:
        print("  WARNING: LA assignment failed - manual lookup needed")
        print(f"  Create: {DATA_DIR}/la_to_region_lookup.csv")
        print(f"  Columns: la_code, region")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Regional file: {REGIONAL_CACHE_CSV}")
    print(f"    {len(regional)} observations "
          f"({regional['region'].nunique()} regions × "
          f"{regional['year'].nunique()} years)")
    if la_df is not None:
        print(f"  LA file: {LA_CACHE_CSV}")
        print(f"    {len(la_df)} observations "
              f"({la_df['la_code'].nunique()} LAs × "
              f"{la_df['year'].nunique()} years)")

    return regional, la_df


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Download HMRC PAYE overseas worker share')
    parser.add_argument('--force', action='store_true',
                        help='Re-download even if cache exists')
    parser.add_argument('--year-min', type=int, default=YEAR_MIN)
    parser.add_argument('--year-max', type=int, default=YEAR_MAX)
    args = parser.parse_args()

    download_paye_overseas(args.year_min, args.year_max, args.force)


if __name__ == '__main__':
    main()
