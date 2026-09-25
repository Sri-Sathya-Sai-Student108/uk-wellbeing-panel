#!/usr/bin/env python3
"""
skills_for_care.py - Parse Skills for Care ASCWDS trended data.

Reads the trended data Excel file (independent sector, all services,
all job roles, LA level) and outputs a clean panel CSV with ONS codes.

Source file:
  data/skillsforcare/Trendeddatadownload201617to202324.xlsx
  Download from: https://www.skillsforcare.org.uk/Adult-Social-Care-
    Workforce-Data/workforceintelligence/resources/Local-authority-areas.aspx

Output:
  data/intermediate/skillsforcare_england.csv

    la_code, la_name, year, filled_posts, employees, vacant_posts,
    vacancy_rate, fte_posts

Boundary handling
-----------------
SfC uses upper-tier LA geography (151 areas). Three county-level
boundary changes during the study period require combining:

  DORSET_COMBINED (DORSET_COMBINED):
    2016-2018: Bournemouth + Poole + Dorset (county, includes Christchurch)
    2019-2023: Bournemouth Christchurch and Poole + Dorset

  NORTHANTS_COMBINED:
    2016-2020: Northamptonshire (county)
    2021-2023: North Northamptonshire + West Northamptonshire

  CUMBRIA_COMBINED:
    2016-2022: Cumbria (county)
    2023:      Cumberland + Westmorland and Furness

Suppressed values
-----------------
Small LAs have vacant posts and vacancy rate suppressed (*).
These are replaced with NaN. Filled posts and employees are never
suppressed in this dataset.

Year mapping
------------
SfC fiscal years (e.g. 2020/21) are mapped to the starting calendar
year (2020). This aligns with Rama's panel which uses calendar years.

Usage:
  python skills_for_care.py
  python make.py skillsforcare
"""

import os
import re
import difflib
import warnings

import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')

from config import DATA_DIR

SFC_DIR      = os.path.join(DATA_DIR, 'skillsforcare')
SFC_FILE     = os.path.join(SFC_DIR, 'Trendeddatadownload201617to202324.xlsx')
SFC_SHEET    = 'Trended data - 16-17 to 23-24'
INTERMEDIATE = os.path.join(DATA_DIR, 'intermediate')
OUTPUT_FILE  = os.path.join(INTERMEDIATE, 'skillsforcare_england.csv')

YEAR_MIN = 2016
YEAR_MAX = 2023

# ---------------------------------------------------------------------------
# Name → ONS code mapping
# ---------------------------------------------------------------------------
# SfC uses LA names rather than codes, with various spelling differences
# from ONS LAD23 names. This dict maps SfC names → ONS LAD23 codes
# for all cases that don't match directly after normalisation.

SFC_NAME_TO_CODE = {
    # Ampersand → and
    'Barking & Dagenham':           'E09000002',
    'Brighton & Hove':              'E06000043',
    'Cheshire West & Chester':      'E06000050',
    'Hammersmith & Fulham':         'E09000013',
    'Kensington & Chelsea':         'E09000020',
    'Redcar & Cleveland':           'E06000003',
    'Telford & Wrekin':             'E06000020',
    'Windsor & Maidenhead':         'E06000040',

    # Hyphen / spacing differences
    'Southend on Sea':              'E06000033',
    'St Helens':                    'E08000013',
    'Stockton on Tees':             'E06000004',
    'Stoke on Trent':               'E06000021',

    # Name differences
    'Bristol':                      'E06000023',  # full: Bristol, City of
    'Kingston upon Hull':           'E06000010',  # full: Kingston upon Hull, City of
    'Cornwall and Isles of Scilly': 'E06000052',  # Scilly (E06000053) tiny, use Cornwall

    # Pre-merger names (old codes no longer in LAD23)
    # Mapped to combined synthetic codes matching boundaries.py
    'Bournemouth':                  'DORSET_COMBINED',   # 2016-2018 only
    'Poole':                        'DORSET_COMBINED',   # 2016-2018 only
    'Bournemouth Christchurch and Poole': 'DORSET_COMBINED',  # 2019+
    'Dorset':                       'DORSET_COMBINED',   # all years
    'Northamptonshire':             'NORTHANTS_COMBINED',  # 2016-2020
    'North Northamptonshire':       'NORTHANTS_COMBINED',  # 2021-2023
    'West Northamptonshire':        'NORTHANTS_COMBINED',  # 2021-2023
    'Cumbria':                      'CUMBRIA_COMBINED',    # 2016-2022
    'Cumberland':                   'CUMBRIA_COMBINED',    # 2023
    'Westmorland and Furness':      'CUMBRIA_COMBINED',    # 2023
}

# Combined codes that require summing rather than single row mapping
# (multiple SfC rows → one output row per year)
COMBINED_CODES = {'DORSET_COMBINED', 'NORTHANTS_COMBINED', 'CUMBRIA_COMBINED'}

# Direct name matches after simple normalisation (& → and, strip spaces)
# Used as fallback before fuzzy matching
def normalise_name(name):
    """Normalise LA name for matching."""
    name = str(name).strip()
    name = name.replace('&', 'and')
    name = re.sub(r'\s+', ' ', name)
    return name


# ONS LAD23 name → code lookup (built from known codes)
# Full list of English upper-tier LAs — unitaries, met boroughs, London
# boroughs, counties. Used for direct matching after normalisation.
ONS_NAMES = {
    # Counties (E10)
    'Cambridgeshire': 'E10000003', 'Devon': 'E10000008',
    'Derbyshire': 'E10000007', 'Durham': 'E06000047',
    'East Sussex': 'E10000011', 'Essex': 'E10000012',
    'Gloucestershire': 'E10000013', 'Hampshire': 'E10000014',
    'Hertfordshire': 'E10000015', 'Kent': 'E10000016',
    'Lancashire': 'E10000017', 'Leicestershire': 'E10000018',
    'Lincolnshire': 'E10000019', 'Norfolk': 'E10000020',
    'North Yorkshire': 'E06000065', 'Northumberland': 'E06000057',
    'Nottinghamshire': 'E10000024', 'Oxfordshire': 'E10000025',
    'Somerset': 'E06000066', 'Staffordshire': 'E10000028',
    'Suffolk': 'E10000029', 'Surrey': 'E10000030',
    'Warwickshire': 'E10000031', 'West Sussex': 'E10000032',
    'Worcestershire': 'E10000034',
    # Unitaries (E06)
    'Bath and North East Somerset': 'E06000022',
    'Bedford': 'E06000055', 'Blackburn with Darwen': 'E06000008',
    'Blackpool': 'E06000009', 'Bracknell Forest': 'E06000036',
    'Brighton and Hove': 'E06000043',
    'Bristol, City of': 'E06000023',
    'Buckinghamshire': 'E06000060', 'Central Bedfordshire': 'E06000056',
    'Cheshire East': 'E06000049', 'Cheshire West and Chester': 'E06000050',
    'Cornwall': 'E06000052', 'Darlington': 'E06000005',
    'Derby': 'E06000015', 'East Riding of Yorkshire': 'E06000011',
    'Herefordshire, County of': 'E06000019',
    'Herefordshire': 'E06000019',
    'Isle of Wight': 'E06000046', 'Kingston upon Hull, City of': 'E06000010',
    'Leicester': 'E06000016', 'Luton': 'E06000032',
    'Medway': 'E06000035', 'Middlesbrough': 'E06000002',
    'Milton Keynes': 'E06000042', 'North East Lincolnshire': 'E06000012',
    'North Lincolnshire': 'E06000013', 'North Somerset': 'E06000024',
    'Nottingham': 'E06000018', 'Peterborough': 'E06000031',
    'Plymouth': 'E06000026', 'Portsmouth': 'E06000044',
    'Reading': 'E06000038', 'Rutland': 'E06000017',
    'Shropshire': 'E06000051', 'Slough': 'E06000039',
    'South Gloucestershire': 'E06000025',
    'Southend-on-Sea': 'E06000033', 'Swindon': 'E06000030',
    'Telford and Wrekin': 'E06000020', 'Thurrock': 'E06000034',
    'Torbay': 'E06000027', 'Warrington': 'E06000007',
    'West Berkshire': 'E06000037', 'Wiltshire': 'E06000054',
    'Windsor and Maidenhead': 'E06000040', 'Wokingham': 'E06000041',
    'York': 'E06000014',
    # Metropolitan boroughs (E08)
    'Barnsley': 'E08000016', 'Birmingham': 'E08000025',
    'Bolton': 'E08000001', 'Bradford': 'E08000032',
    'Bury': 'E08000002', 'Calderdale': 'E08000033',
    'Coventry': 'E08000026', 'Doncaster': 'E08000017',
    'Dudley': 'E08000027', 'Gateshead': 'E08000020',
    'Kirklees': 'E08000034', 'Knowsley': 'E08000011',
    'Leeds': 'E08000035', 'Liverpool': 'E08000012',
    'Manchester': 'E08000003', 'Newcastle upon Tyne': 'E08000021',
    'North Tyneside': 'E08000022', 'Oldham': 'E08000004',
    'Rochdale': 'E08000005', 'Rotherham': 'E08000018',
    'Salford': 'E08000006', 'Sandwell': 'E08000028',
    'Sefton': 'E08000014', 'Sheffield': 'E08000019',
    'Solihull': 'E08000029', 'South Tyneside': 'E08000023',
    'Southampton': 'E06000045', 'St. Helens': 'E08000013',
    'Stockport': 'E08000007', 'Stockton-on-Tees': 'E06000004',
    'Stoke-on-Trent': 'E06000021', 'Sunderland': 'E08000024',
    'Tameside': 'E08000008', 'Trafford': 'E08000009',
    'Wakefield': 'E08000036', 'Walsall': 'E08000030',
    'Wigan': 'E08000010', 'Wirral': 'E08000015',
    'Wolverhampton': 'E08000031',
    # London boroughs (E09)
    'Barking and Dagenham': 'E09000002', 'Barnet': 'E09000003',
    'Bexley': 'E09000004', 'Brent': 'E09000005',
    'Bromley': 'E09000006', 'Camden': 'E09000007',
    'City of London': 'E09000001', 'Croydon': 'E09000008',
    'Ealing': 'E09000009', 'Enfield': 'E09000010',
    'Greenwich': 'E09000011', 'Hackney': 'E09000012',
    'Hammersmith and Fulham': 'E09000013', 'Haringey': 'E09000014',
    'Harrow': 'E09000015', 'Havering': 'E09000016',
    'Hillingdon': 'E09000017', 'Hounslow': 'E09000018',
    'Islington': 'E09000019', 'Kensington and Chelsea': 'E09000020',
    'Kingston upon Thames': 'E09000021', 'Lambeth': 'E09000022',
    'Lewisham': 'E09000023', 'Merton': 'E09000024',
    'Newham': 'E09000025', 'Redbridge': 'E09000026',
    'Richmond upon Thames': 'E09000027', 'Southwark': 'E09000028',
    'Sutton': 'E09000029', 'Tower Hamlets': 'E09000030',
    'Waltham Forest': 'E09000031', 'Wandsworth': 'E09000032',
    'Westminster': 'E09000033',
    # Halton is E06
    'Halton': 'E06000006',
    # Hartlepool
    'Hartlepool': 'E06000001',
    # Redcar and Cleveland
    'Redcar and Cleveland': 'E06000003',
}


def map_sfc_name_to_code(sfc_name):
    """
    Map a Skills for Care LA name to an ONS code.

    Priority:
    1. Hard-coded SFC_NAME_TO_CODE dict (boundary cases + known mismatches)
    2. Direct lookup in ONS_NAMES
    3. Normalised name lookup (& → and, strip)
    4. Fuzzy match as last resort
    """
    # 1. Hard-coded
    if sfc_name in SFC_NAME_TO_CODE:
        return SFC_NAME_TO_CODE[sfc_name]

    # 2. Direct
    if sfc_name in ONS_NAMES:
        return ONS_NAMES[sfc_name]

    # 3. Normalised
    norm = normalise_name(sfc_name)
    for ons_name, code in ONS_NAMES.items():
        if normalise_name(ons_name) == norm:
            return code

    # 4. Fuzzy
    ons_norm = {normalise_name(n): c for n, c in ONS_NAMES.items()}
    matches = difflib.get_close_matches(norm, ons_norm.keys(),
                                        n=1, cutoff=0.8)
    if matches:
        return ons_norm[matches[0]]

    return None


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def load_skills_for_care(year_min=YEAR_MIN, year_max=YEAR_MAX,
                          force_refresh=False):
    """
    Parse Skills for Care ASCWDS trended data.

    Returns DataFrame: la_code, la_name, year, filled_posts, employees,
                       vacant_posts, vacancy_rate, fte_posts
    """
    os.makedirs(INTERMEDIATE, exist_ok=True)

    if os.path.exists(OUTPUT_FILE) and not force_refresh:
        print(f"  Loading cached SfC data from {OUTPUT_FILE}...")
        df = pd.read_csv(OUTPUT_FILE)
        print(f"  {len(df)} obs, {df['la_code'].nunique()} LAs, "
              f"years {df['year'].min()}-{df['year'].max()}")
        return df

    if not os.path.exists(SFC_FILE):
        print(f"  ERROR: File not found: {SFC_FILE}")
        print(f"  Download from:")
        print(f"  https://www.skillsforcare.org.uk/Adult-Social-Care-Workforce-Data"
              f"/workforceintelligence/resources/Local-authority-areas.aspx")
        print(f"  Save as: {SFC_FILE}")
        return None

    print(f"  Reading {SFC_FILE}...")
    raw = pd.read_excel(SFC_FILE, sheet_name=SFC_SHEET)

    # Filter to independent sector, all services, all job roles, LA level
    df = raw[
        (raw['Area Level'] == 'Local authority') &
        (raw['Sector'] == 'Independent') &
        (raw['Service'] == 'All services') &
        (raw['Job role group'] == 'All job roles')
    ].copy()

    print(f"  Filtered: {len(df)} rows, {df['Local authority'].nunique()} LAs")

    # Map fiscal year to starting calendar year (2020/21 → 2020)
    df['year'] = df['Year'].str[:4].astype(int)
    df = df[(df['year'] >= year_min) & (df['year'] <= year_max)]

    # Rename columns
    df = df.rename(columns={
        'Local authority':              'la_name',
        'Filled posts - All sectors':   'filled_posts',
        'Employees':                    'employees',
        'Vacant posts':                 'vacant_posts',
        'Vacancy rate':                 'vacancy_rate',
        'FTE Filled posts - All sectors': 'fte_posts',
    })

    # Handle suppressed values (*)
    for col in ['vacant_posts', 'vacancy_rate', 'fte_posts']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace('*', np.nan),
                                    errors='coerce')

    # Ensure numeric
    for col in ['filled_posts', 'employees']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    keep = ['la_name', 'year', 'filled_posts', 'employees',
            'vacant_posts', 'vacancy_rate', 'fte_posts']
    df = df[[c for c in keep if c in df.columns]].copy()

    # Map names to ONS codes
    print("  Mapping LA names to ONS codes...")
    df['la_code'] = df['la_name'].map(map_sfc_name_to_code)

    # Report unmapped
    unmapped = df[df['la_code'].isna()]['la_name'].unique()
    if len(unmapped) > 0:
        print(f"  WARNING: {len(unmapped)} names not mapped:")
        for n in sorted(unmapped):
            print(f"    '{n}'")

    df = df.dropna(subset=['la_code'])

    # Combine split/merged authorities by summing filled posts etc.
    # and averaging rates (vacancy_rate = vacant_posts / filled_posts)
    print("  Combining boundary split authorities...")
    df = _combine_splits(df)

    df = df.sort_values(['la_code', 'year']).reset_index(drop=True)

    # Summary
    print(f"\n  Skills for Care panel:")
    print(f"  LAs: {df['la_code'].nunique()}")
    print(f"  Years: {sorted(df['year'].unique())}")
    print(f"  Observations: {len(df)}")

    n_vacant_null = df['vacant_posts'].isna().sum()
    if n_vacant_null > 0:
        pct = n_vacant_null / len(df) * 100
        print(f"  Suppressed vacant posts: {n_vacant_null} ({pct:.1f}%) — "
              f"set to NaN (small LA suppression)")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"  Saved: {OUTPUT_FILE}")
    return df


def _combine_splits(df):
    """
    Combine rows for split/merged authorities into single rows per year.

    For stock variables (filled_posts, employees, vacant_posts, fte_posts):
        combined = sum of parts
    For rate variables (vacancy_rate):
        recomputed as vacant_posts / (filled_posts + vacant_posts)

    Handles:
        DORSET_COMBINED:     Bournemouth + Poole + Dorset (2016-18)
                             BCP + Dorset (2019-23)
        NORTHANTS_COMBINED:  Northamptonshire (2016-20)
                             North + West Northants (2021-23)
        CUMBRIA_COMBINED:    Cumbria (2016-22)
                             Cumberland + Westmorland (2023)
    """
    stock_cols = ['filled_posts', 'employees', 'vacant_posts', 'fte_posts']
    stock_cols = [c for c in stock_cols if c in df.columns]

    # Separate combined and non-combined rows
    combined_mask = df['la_code'].isin(COMBINED_CODES)
    non_combined = df[~combined_mask].copy()
    to_combine   = df[combined_mask].copy()

    if len(to_combine) == 0:
        return df

    # Aggregate: sum stocks per combined code per year
    agg = to_combine.groupby(['la_code', 'year']).agg(
        {col: 'sum' for col in stock_cols}
    ).reset_index()

    # Recompute vacancy rate from aggregated stocks
    if 'vacant_posts' in agg.columns and 'filled_posts' in agg.columns:
        total_posts = agg['filled_posts'] + agg['vacant_posts'].fillna(0)
        agg['vacancy_rate'] = np.where(
            total_posts > 0,
            agg['vacant_posts'] / total_posts,
            np.nan
        )

    # Add readable names for combined authorities
    combined_names = {
        'DORSET_COMBINED':    'Dorset (combined)',
        'NORTHANTS_COMBINED': 'Northamptonshire (combined)',
        'CUMBRIA_COMBINED':   'Cumbria (combined)',
    }
    agg['la_name'] = agg['la_code'].map(combined_names)

    # Report
    for code in sorted(agg['la_code'].unique()):
        n = len(agg[agg['la_code'] == code])
        print(f"    {combined_names[code]}: {n} combined rows")

    return pd.concat([non_combined, agg], ignore_index=True)


# ---------------------------------------------------------------------------
# Standalone run
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Parse Skills for Care ASCWDS data')
    parser.add_argument('--force', action='store_true',
                        help='Re-parse even if cache exists')
    parser.add_argument('--year-min', type=int, default=YEAR_MIN)
    parser.add_argument('--year-max', type=int, default=YEAR_MAX)
    args = parser.parse_args()

    print("=" * 60)
    print("SKILLS FOR CARE ASCWDS PARSER")
    print("=" * 60)
    print()
    result = load_skills_for_care(
        year_min=args.year_min,
        year_max=args.year_max,
        force_refresh=args.force
    )
    if result is not None:
        print()
        print("Sample output:")
        print(result.head(10).to_string(index=False))
