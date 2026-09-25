#!/usr/bin/env python3
"""
panel_data.py - Shared data download functions for England and Scotland panels.

Provides:
  download_claimant_count()  - Nomis Experimental Claimant Count, annual mean,
                               LA level, 2016-2023, UK-wide
  download_population()      - ONS Mid-Year Estimates, LA level, 2016-2023,
                               total population + aged 60+

Both functions cache results to data/intermediate/ to avoid repeat API calls.

Vacancy data notes
------------------
England (Skills for Care ASCWDS):
  Monthly administrative data, aggregated to annual mean.
  Loaded separately in england_panel.py.

Scotland (SSSC / Care Inspectorate joint report):
  Annual snapshot at 31 December each year.
  Reports available: 2019, 2020, 2021, 2022, 2023.
  Tables published as CSV/Excel at:
    https://data.sssc.uk.com/data-publications/30-vacancy-reports
  Local authority level detail available as supplementary spreadsheets at:
    https://data.sssc.uk.com/local-level-data
  Data must be downloaded manually (no API) and saved as:
    data/scotland_vacancies.csv  (columns: la_code, year, vacancies_wte,
                                  vacancy_rate)
  Note: December snapshot vs England annual mean is a data constraint,
  not a methodological choice. Documented in paper Methods section.

Usage:
  from panel_data import download_claimant_count, download_population
"""

import os
import time
import warnings

import pandas as pd
import numpy as np
import requests

warnings.filterwarnings('ignore')

from config import DATA_DIR

INTERMEDIATE_DIR = os.path.join(DATA_DIR, 'intermediate')

# ---------------------------------------------------------------------------
# Nomis API constants
# ---------------------------------------------------------------------------
NOMIS_BASE   = 'https://www.nomisweb.co.uk/api/v01/dataset'
NOMIS_CC_ID  = 'NM_162_1'   # Experimental Claimant Count (JSA + UC)
NOMIS_GEO    = 'TYPE464'    # Local Authority Districts (UK-wide)
                             # Note: TYPE460 = parliamentary constituencies (wrong)

CC_CACHE     = os.path.join(INTERMEDIATE_DIR, 'claimant_count_annual.csv')
POP_CACHE    = os.path.join(INTERMEDIATE_DIR, 'population_annual.csv')

YEAR_MIN = 2016
YEAR_MAX = 2023


# ---------------------------------------------------------------------------
# Claimant Count
# ---------------------------------------------------------------------------

def _fetch_claimant_month(year, month, session, retries=3):
    """
    Fetch claimant count for all UK LAs for one month via Nomis API.
    Returns DataFrame: la_code, la_name, claimants
    """
    date_str = f"{year}-{month:02d}"
    url = (
        f"{NOMIS_BASE}/{NOMIS_CC_ID}/data.csv"
        f"?geography={NOMIS_GEO}"
        f"&date={date_str}"
        f"&gender=0"          # total (male + female)
        f"&age=0"             # total (all ages)
        f"&measure=1"         # claimants (count)
        f"&measures=20100"    # value
        f"&select=date_name,geography_name,geography_code,obs_value"
        f"&uid=0xnomisanon"
    )

    for attempt in range(retries):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 100:
                df = pd.read_csv(pd.io.common.StringIO(resp.text))
                df.columns = df.columns.str.lower().str.strip()
                df = df.rename(columns={
                    'geography_code': 'la_code',
                    'geography_name': 'la_name',
                    'obs_value':      'claimants'
                })
                df['claimants'] = pd.to_numeric(df['claimants'], errors='coerce')
                return df[['la_code', 'la_name', 'claimants']].dropna()
            else:
                time.sleep(2 ** attempt)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    WARNING: Failed to fetch {date_str}: {e}")
    return None


def download_claimant_count(year_min=YEAR_MIN, year_max=YEAR_MAX,
                             force_refresh=False):
    """
    Download Experimental Claimant Count (JSA + UC) from Nomis at LA level.

    Produces TWO claimant variables per LA per year:
      claimants_december - December snapshot (matches Radakrishnan et al. 2025)
      claimants_annual   - Annual mean (Jan-Dec, for internal consistency
                           with annual Skills for Care data)

    Note on COVID timing:
      December 2020 is elevated (post-COVID surge). Annual mean 2020 is
      lower (pre-COVID months pull it down). The two measures tell different
      stories about the retail employment effect — see RETAIL_METHODOLOGY_NOTE.md.

    Caches to data/intermediate/claimant_count_annual.csv.
    Returns DataFrame: la_code, la_name, year, claimants_december, claimants_annual
    """
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

    if os.path.exists(CC_CACHE) and not force_refresh:
        print(f"  Loading cached claimant count from {CC_CACHE}...")
        df = pd.read_csv(CC_CACHE)
        print(f"  {len(df)} observations, "
              f"years {df['year'].min()}-{df['year'].max()}, "
              f"{df['la_code'].nunique()} LAs")
        return df

    print(f"  Downloading claimant count from Nomis (NM_162_1)...")
    print(f"  Period: {year_min}-{year_max}")
    print(f"  Fetching all 12 months + December snapshot")
    print(f"  Geography: all UK local authority districts (TYPE464)")

    session    = requests.Session()
    all_monthly = []

    for year in range(year_min, year_max + 1):
        print(f"    Year {year}:", end=' ', flush=True)
        year_data = []

        for month in range(1, 13):
            df_month = _fetch_claimant_month(year, month, session)
            if df_month is not None and len(df_month) > 0:
                df_month['year']  = year
                df_month['month'] = month
                year_data.append(df_month)
                print('.', end='', flush=True)
            else:
                print('x', end='', flush=True)
            time.sleep(0.3)

        if year_data:
            year_df = pd.concat(year_data, ignore_index=True)
            all_monthly.append(year_df)
            print(f" ({year_df['month'].nunique()} months, "
                  f"{year_df['la_code'].nunique()} LAs)")
        else:
            print(f" WARNING: no data")

    if not all_monthly:
        print("  ERROR: No claimant count data downloaded")
        return None

    monthly = pd.concat(all_monthly, ignore_index=True)

    # December snapshot
    dec = (monthly[monthly['month'] == 12]
           .groupby(['la_code', 'la_name', 'year'])
           .agg(claimants_december=('claimants', 'first'))
           .reset_index())

    # Annual mean
    ann = (monthly
           .groupby(['la_code', 'la_name', 'year'])
           .agg(claimants_annual=('claimants', 'mean'),
                claimants_months=('month', 'count'))
           .reset_index())
    ann['claimants_annual'] = ann['claimants_annual'].round(1)

    # Merge
    annual = dec.merge(ann[['la_code', 'year', 'claimants_annual',
                             'claimants_months']],
                       on=['la_code', 'year'], how='left')

    # Apply boundary harmonisation
    print("  Applying boundary harmonisation...")
    try:
        from boundaries import harmonise_boundaries, remap_scottish_codes

        def harmonise_col(df, col):
            df_long = df[['la_code', 'la_name', 'year', col]].copy()
            df_long = df_long.rename(columns={col: 'value'})
            df_long['measure'] = col
            df_long['period']  = df_long['year'].astype(str)
            df_long = harmonise_boundaries(df_long)
            df_long = remap_scottish_codes(df_long)
            return df_long.rename(columns={'value': col})[
                ['la_code', 'la_name', 'year', col]]

        dec_h = harmonise_col(annual, 'claimants_december')
        ann_h = harmonise_col(annual, 'claimants_annual')

        annual = dec_h.merge(
            ann_h[['la_code', 'year', 'claimants_annual']],
            on=['la_code', 'year'], how='left'
        )
        print(f"  After harmonisation: {annual['la_code'].nunique()} LAs")

    except Exception as e:
        print(f"  WARNING: Boundary harmonisation failed: {e}")

    annual.to_csv(CC_CACHE, index=False)
    print(f"\n  Saved: {CC_CACHE}")
    print(f"  Columns: claimants_december (R's approach) + "
          f"claimants_annual (for sensitivity)")
    print(f"  {len(annual)} observations, "
          f"{annual['la_code'].nunique()} LAs, "
          f"years {annual['year'].min()}-{annual['year'].max()}")

    return annual


# ---------------------------------------------------------------------------
# Population
# ---------------------------------------------------------------------------

NOMIS_DIR      = os.path.join(DATA_DIR, 'nomis')
NOMIS_POP_FILE = os.path.join(NOMIS_DIR, 'NOMIS_POP.csv')


def download_population(year_min=YEAR_MIN, year_max=YEAR_MAX,
                        force_refresh=False):
    """
    Parse ONS Mid-Year Population Estimates from manually downloaded Nomis CSV.

    File downloaded manually from:
      https://www.nomisweb.co.uk/datasets/pestsyoala
    Select: local authorities district/unitary (April 2023), all areas,
    years 2016-2023, Gender=Total, Age selections: All ages + 0-15 + 16-64.
    Save as: data/nomis/NOMIS_POP.csv

    File structure (wide format, multiple rows per LA):
      Row 1 per LA: Total, All Ages  -> pop_total
      Row 2 per LA: Total, 16-64     (combined to derive pop_65plus)
      Row 3 per LA: Total, 0-15      (combined to derive pop_65plus)

    Age threshold note:
      We use 65+ rather than 60+ because the 60-64 age band is bundled
      into the 16-64 Nomis selection and cannot be separated without an
      additional download. 65 is the conventional retirement threshold
      in labour market literature. Population is a control variable;
      this approximation does not materially affect results.
      Documented in paper Methods section.

    Returns DataFrame: la_code, la_name, year, pop_total, pop_65plus
    """
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)

    if os.path.exists(POP_CACHE) and not force_refresh:
        print(f"  Loading cached population from {POP_CACHE}...")
        df = pd.read_csv(POP_CACHE)
        print(f"  {len(df)} obs, {df['la_code'].nunique()} LAs, "
              f"years {df['year'].min()}-{df['year'].max()}")
        return df

    if not os.path.exists(NOMIS_POP_FILE):
        print(f"  ERROR: File not found: {NOMIS_POP_FILE}")
        print(f"  Download from https://www.nomisweb.co.uk/datasets/pestsyoala")
        print(f"  Select: all district/unitary LAs, 2016-2023, Total,")
        print(f"          Age = All ages + 0-15 + 16-64")
        print(f"  Save as: {NOMIS_POP_FILE}")
        return None

    print(f"  Parsing {NOMIS_POP_FILE}...")

    # Skip 6 metadata rows, read wide-format table
    raw = pd.read_csv(NOMIS_POP_FILE, skiprows=6, quotechar='"',
                      low_memory=False)
    raw.columns = [str(c).strip() for c in raw.columns]

    # Keep only LA-level rows (ladu2023: prefix)
    la_raw = raw[raw['Area'].str.startswith('ladu2023:', na=False)].copy()
    la_raw['la_name_raw'] = (la_raw['Area']
                              .str.replace('ladu2023:', '', regex=False))

    # Year columns in study range
    year_cols = [c for c in la_raw.columns
                 if c.isdigit() and year_min <= int(c) <= year_max]

    # Multiple rows per LA: row 0 = All Ages total, row 1 = 16-64, row 2 = 0-15
    # (rows 3+ are female/male breakdowns - not needed)
    la_raw = la_raw.reset_index(drop=True)
    la_raw['row_n'] = la_raw.groupby('la_name_raw').cumcount()

    def melt_rows(row_n, value_name):
        sub = la_raw[la_raw['row_n'] == row_n][['la_name_raw'] + year_cols]
        m = sub.melt(id_vars='la_name_raw', value_vars=year_cols,
                     var_name='year', value_name=value_name)
        m['year'] = m['year'].astype(int)
        m[value_name] = pd.to_numeric(m[value_name], errors='coerce')
        return m

    df_tot  = melt_rows(0, 'pop_total')
    df_1664 = melt_rows(1, 'pop_16_64')
    df_015  = melt_rows(2, 'pop_0_15')

    pop = (df_tot
           .merge(df_1664, on=['la_name_raw', 'year'])
           .merge(df_015,  on=['la_name_raw', 'year']))

    # 65+ = total - working age - children
    pop['pop_65plus'] = (pop['pop_total']
                         - pop['pop_16_64']
                         - pop['pop_0_15']).clip(lower=0)
    pop = pop.drop(columns=['pop_16_64', 'pop_0_15'])

    # Map LA names to ONS codes using cached boundary file
    print("  Mapping LA names to ONS codes...")
    try:
        import geopandas as gpd
        boundary_cache = os.path.join(DATA_DIR, 'la_boundaries_lad23.geojson')
        if os.path.exists(boundary_cache):
            gdf = gpd.read_file(boundary_cache)
            code_col = next((c for c in ['LAD23CD','LAD22CD','lad23cd','CODE']
                             if c in gdf.columns), None)
            name_col = next((c for c in ['LAD23NM','LAD22NM','lad23nm','NAME']
                             if c in gdf.columns), None)
            if code_col and name_col:
                name_to_code = dict(zip(gdf[name_col], gdf[code_col]))
                pop['la_code'] = pop['la_name_raw'].map(name_to_code)
                pop['la_name'] = pop['la_name_raw']
                unmatched = pop[pop['la_code'].isna()]['la_name_raw'].unique()
                if len(unmatched) > 0:
                    print(f"  WARNING: {len(unmatched)} LA names unmatched:")
                    for n in sorted(unmatched)[:10]:
                        print(f"    '{n}'")
            else:
                pop['la_code'] = None
                pop['la_name'] = pop['la_name_raw']
        else:
            print("  WARNING: Boundary file not cached - run maps.py first")
            pop['la_code'] = None
            pop['la_name'] = pop['la_name_raw']
    except Exception as e:
        print(f"  WARNING: Name->code mapping failed: {e}")
        pop['la_code'] = None
        pop['la_name'] = pop['la_name_raw']

    pop = pop.drop(columns=['la_name_raw'])

    # Sanity check
    pct = (pop['pop_65plus'] / pop['pop_total'] * 100).mean()
    print(f"\n  Sanity check: mean % aged 65+ = {pct:.1f}% (expect ~18-21%)")
    if not (14 <= pct <= 28):
        print("  WARNING: % outside expected range - check age bands")

    pop = pop[['la_code', 'la_name', 'year',
               'pop_total', 'pop_65plus']].dropna(subset=['pop_total'])

    pop.to_csv(POP_CACHE, index=False)
    print(f"  Saved: {POP_CACHE}")
    print(f"  {len(pop)} obs, {pop['la_code'].nunique()} LAs, "
          f"years {pop['year'].min()}-{pop['year'].max()}")
    return pop




# ---------------------------------------------------------------------------
# Convenience: download both
# ---------------------------------------------------------------------------

def download_shared_data(year_min=YEAR_MIN, year_max=YEAR_MAX,
                          force_refresh=False):
    """Download claimant count and population. Returns (cc_df, pop_df)."""
    print("=" * 60)
    print("DOWNLOADING SHARED PANEL DATA")
    print("=" * 60)

    print("\n1. Claimant Count (Nomis NM_162_1)...")
    cc_df = download_claimant_count(year_min, year_max, force_refresh)

    print("\n2. Population Estimates (Nomis NM_31_1)...")
    pop_df = download_population(year_min, year_max, force_refresh)

    return cc_df, pop_df


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Download shared panel data (claimants + population)')
    parser.add_argument('--force', action='store_true',
                        help='Re-download even if cache exists')
    parser.add_argument('--claimants-only', action='store_true')
    parser.add_argument('--population-only', action='store_true')
    args = parser.parse_args()

    if args.claimants_only:
        download_claimant_count(force_refresh=args.force)
    elif args.population_only:
        download_population(force_refresh=args.force)
    else:
        download_shared_data(force_refresh=args.force)
