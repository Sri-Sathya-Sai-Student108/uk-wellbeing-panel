#!/usr/bin/env python3
"""
assemble_england_sfc.py - Add Skills for Care and retail data to England panel.

Takes the base England panel (assemble_england.py output) and adds:
  - Retail counts aggregated from lower-tier LADs to upper-tier LAs
  - Claimants aggregated to upper-tier
  - Population aggregated to upper-tier
  - Skills for Care workforce outcomes (already at upper-tier)

The resulting panel matches Rama's ~149 upper-tier LA geography.

Geography note
--------------
Skills for Care uses upper-tier local authority geography (counties +
unitaries). The base panel uses lower-tier LADs (296 English LAs including
districts). Districts (E07) are aggregated to their county (E10) using the
ONS LAD-to-County lookup (data/lad_to_county.csv).

Unitaries (E06), met boroughs (E08) and London boroughs (E09) map 1:1.
Combined split codes (DORSET_COMBINED etc.) are retained as-is.

Dependencies
------------
  python make.py england-panel     # base panel
  python make.py skillsforcare     # SfC data
  data/lad_to_county.csv           # ONS district->county lookup

Output
------
  data/intermediate/england_panel_sfc.csv

  la_code, la_name, year, nation,
  tot, tot_new, tot_old,
  claimants_december, claimants_annual, pop_total, pop_65plus,
  overseas_share, region,
  filled_posts, employees, vacant_posts, vacancy_rate, fte_posts,
  + wellbeing columns (measure, value, se, ci_lower, ci_upper)

Usage:
  python assemble_england_sfc.py
  python assemble_england_sfc.py --force
  python make.py england-sfc
"""

import os, sys, warnings
import pandas as pd
import numpy as np
warnings.filterwarnings('ignore')

from config import DATA_DIR

INTERMEDIATE  = os.path.join(DATA_DIR, 'intermediate')
OUTPUT_FILE   = os.path.join(INTERMEDIATE, 'england_panel_sfc.csv')

BASE_FILE     = os.path.join(INTERMEDIATE, 'england_panel_base.csv')
RETAIL_FILE   = os.path.join(INTERMEDIATE, 'retail_data_england.csv')
SFC_FILE      = os.path.join(INTERMEDIATE, 'skillsforcare_england.csv')
LAD_CTY_FILE  = os.path.join(DATA_DIR,     'lad_to_county.csv')


def get_lad_to_county():
    """
    Load LAD->County lookup, downloading from ONS if not cached.
    233 English districts (E07) mapped to their county (E10).
    Cached to data/lad_to_county.csv.
    """
    if os.path.exists(LAD_CTY_FILE):
        df = pd.read_csv(LAD_CTY_FILE)
        print(f"  Loaded LAD->County lookup ({len(df)} districts)")
        return df

    print("  Downloading LAD->County lookup from ONS Open Geography Portal...")
    try:
        import requests
        url = (
            "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
            "LAD23_CTY23_EN_LU/FeatureServer/0/query"
            "?where=1%3D1&outFields=LAD23CD,LAD23NM,CTY23CD,CTY23NM"
            "&f=json&resultRecordCount=500"
        )
        resp = requests.get(url, timeout=30)
        records = [f['attributes'] for f in resp.json().get('features', [])]
        df = pd.DataFrame(records)
        df.columns = ['lad_code', 'lad_name', 'cty_code', 'cty_name']
        df.to_csv(LAD_CTY_FILE, index=False)
        print(f"  Downloaded and cached {len(df)} district->county mappings")
        return df
    except Exception as e:
        print(f"  ERROR downloading lookup: {e}")
        return None


def check_inputs():
    required = {
        'Base England panel':    BASE_FILE,
        'Retail England':        RETAIL_FILE,
        'Skills for Care':       SFC_FILE,
    }
    missing = {k: v for k, v in required.items() if not os.path.exists(v)}
    if missing:
        print("\nERROR: Missing input files:")
        for name, path in missing.items():
            print(f"  {name}: {path}")
        print("\nRun:")
        print("  python make.py england-panel")
        print("  python make.py skillsforcare")
        return False
    return True


def build_upper_tier_map(lad_cty_df):
    """
    Build two dicts from the LAD->County lookup:
      code_map: lad_code -> cty_code  (for aggregation)
      name_map: cty_code -> cty_name  (for labelling after aggregation)
    """
    code_map = dict(zip(lad_cty_df['lad_code'], lad_cty_df['cty_code']))
    name_map = dict(zip(lad_cty_df['cty_code'], lad_cty_df['cty_name']))
    return code_map, name_map


def upper_tier_code(la_code, district_map):
    """Map a LAD code to its upper-tier equivalent."""
    if str(la_code).startswith('E07'):
        return district_map.get(la_code, la_code)
    return la_code


def aggregate_to_upper_tier(df, district_map, name_map=None, year_col='year',
                             sum_cols=None, mean_cols=None):
    """
    Aggregate a lower-tier LA DataFrame to upper-tier geography.
    After aggregation, updates la_name for E10 counties using name_map.

    sum_cols:  columns to sum (counts)
    mean_cols: columns to average (rates)
    """
    df = df.copy()
    df['_upper'] = df['la_code'].apply(
        lambda c: upper_tier_code(c, district_map)
    )

    agg = {}
    if sum_cols:
        for c in sum_cols:
            if c in df.columns:
                agg[c] = 'sum'
    if mean_cols:
        for c in mean_cols:
            if c in df.columns:
                agg[c] = 'mean'

    # Always take first for string/identifier cols
    for c in ['la_name', 'nation', 'region']:
        if c in df.columns and c not in agg:
            agg[c] = 'first'

    group_cols = ['_upper', year_col]
    if 'measure' in df.columns:
        group_cols.append('measure')

    result = df.groupby(group_cols).agg(agg).reset_index()
    result = result.rename(columns={'_upper': 'la_code'})

    # Fix county names: E10 codes get the proper county name
    # (not the first district name which is what 'first' gives us)
    if name_map and 'la_name' in result.columns:
        result['la_name'] = result.apply(
            lambda r: name_map.get(r['la_code'], r['la_name']),
            axis=1
        )

    return result


def assemble_england_sfc_panel(force_refresh=False):
    """
    Build upper-tier England panel with Skills for Care data.
    """
    os.makedirs(INTERMEDIATE, exist_ok=True)

    if os.path.exists(OUTPUT_FILE) and not force_refresh:
        print(f"  Loading cached England SfC panel from {OUTPUT_FILE}...")
        df = pd.read_csv(OUTPUT_FILE)
        print(f"  {len(df):,} obs, {df['la_code'].nunique()} LAs, "
              f"years {df['year'].min()}-{df['year'].max()}")
        return df

    if not check_inputs():
        return None

    print("\n1. Loading inputs...")
    base   = pd.read_csv(BASE_FILE)
    retail = pd.read_csv(RETAIL_FILE)
    sfc    = pd.read_csv(SFC_FILE)
    lad_cty = get_lad_to_county()
    if lad_cty is None:
        print("ERROR: Cannot proceed without LAD->County lookup")
        return None

    print(f"  Base panel:      {base['la_code'].nunique()} LAs, "
          f"{len(base):,} obs")
    print(f"  Retail:          {retail['la_code'].nunique()} lower-tier LAs")
    print(f"  Skills for Care: {sfc['la_code'].nunique()} upper-tier LAs")
    print(f"  LAD->County:     {len(lad_cty)} district mappings")

    # Build district->county map and county name map
    print("\n2. Building upper-tier geography map...")
    district_map, name_map = build_upper_tier_map(lad_cty)

    n_districts = retail[retail['la_code'].str.startswith('E07',
                         na=False)]['la_code'].nunique()
    n_mapped = sum(1 for c in retail['la_code'].unique()
                   if str(c).startswith('E07') and c in district_map)
    print(f"  Districts in retail: {n_districts}, mapped: {n_mapped}")

    unmapped = [c for c in retail['la_code'].unique()
                if str(c).startswith('E07') and c not in district_map]
    if unmapped:
        print(f"  WARNING: {len(unmapped)} unmapped districts: {unmapped[:5]}")

    # Aggregate retail to upper-tier
    print("\n3. Aggregating retail to upper-tier...")
    retail_ut = aggregate_to_upper_tier(
        retail, district_map, name_map,
        sum_cols=['tot', 'tot_new', 'tot_old']
    )
    print(f"  Retail: {retail['la_code'].nunique()} lower -> "
          f"{retail_ut['la_code'].nunique()} upper-tier LAs")

    # Split base panel into non-wellbeing (wide) and wellbeing (long)
    wb_cols = ['la_code', 'year', 'measure', 'value', 'se',
               'ci_lower', 'ci_upper']
    base_cols = ['la_code', 'la_name', 'year', 'nation', 'region',
                 'claimants_december', 'claimants_annual', 'pop_total', 'pop_65plus',
                 'overseas_share']

    base_wide = base[[c for c in base_cols if c in base.columns]].drop_duplicates(
        subset=['la_code', 'year']
    )
    base_wb = base[[c for c in wb_cols if c in base.columns]]

    print("\n4. Aggregating base panel to upper-tier...")
    base_ut = aggregate_to_upper_tier(
        base_wide, district_map, name_map,
        sum_cols=['claimants_december', 'claimants_annual', 'pop_total', 'pop_65plus'],
        mean_cols=['overseas_share']
    )
    print(f"  Base: {base_wide['la_code'].nunique()} lower -> "
          f"{base_ut['la_code'].nunique()} upper-tier LAs")

    wb_ut = aggregate_to_upper_tier(
        base_wb, district_map, name_map,
        mean_cols=['value', 'se', 'ci_lower', 'ci_upper']
    )

    # Combine split authorities manually
    # (combine_splits() from boundaries.py expects wellbeing format)
    print("\n4b. Combining split authorities...")

    SPLITS = {
        'DORSET_COMBINED':    ['E06000058', 'E06000059'],
        'NORTHANTS_COMBINED': ['E06000061', 'E06000062'],
        'CUMBRIA_COMBINED':   ['E06000063', 'E06000064'],
    }
    SPLIT_NAMES = {
        'DORSET_COMBINED':    'Dorset (combined)',
        'NORTHANTS_COMBINED': 'Northamptonshire (combined)',
        'CUMBRIA_COMBINED':   'Cumbria (combined)',
    }

    def combine_split_codes(df, sum_cols, mean_cols, id_col='la_code',
                            year_col='year'):
        """Combine split authority parts into single rows."""
        df = df.copy()
        rows_to_add = []
        codes_to_drop = []

        for combined_code, parts in SPLITS.items():
            for year in df[year_col].unique():
                mask = df[id_col].isin(parts) & (df[year_col] == year)
                part_rows = df[mask]
                if len(part_rows) == 0:
                    continue

                new_row = {id_col: combined_code,
                           year_col: year,
                           'la_name': SPLIT_NAMES[combined_code]}
                if 'nation' in df.columns:
                    new_row['nation'] = 'England'
                if 'region' in df.columns:
                    new_row['region'] = part_rows['region'].iloc[0]

                for col in sum_cols:
                    if col in df.columns:
                        new_row[col] = part_rows[col].sum()
                for col in mean_cols:
                    if col in df.columns:
                        new_row[col] = part_rows[col].mean()

                rows_to_add.append(new_row)

            codes_to_drop.extend(parts)

        df = df[~df[id_col].isin(codes_to_drop)]
        if rows_to_add:
            df = pd.concat([df, pd.DataFrame(rows_to_add)],
                           ignore_index=True)
            print(f"  Combined: {list(SPLITS.keys())}")
        return df

    sum_cols_base = ['claimants_december', 'claimants_annual', 'pop_total', 'pop_65plus']
    mean_cols_base = ['overseas_share']
    sum_cols_retail = ['tot', 'tot_new', 'tot_old']

    retail_ut = combine_split_codes(retail_ut, sum_cols_retail, [])
    base_ut   = combine_split_codes(base_ut, sum_cols_base, mean_cols_base)

    # Wellbeing: combine per measure
    if len(wb_ut) > 0:
        wb_parts = []
        for measure in wb_ut['measure'].dropna().unique():
            wb_m = wb_ut[wb_ut['measure'] == measure].copy()
            wb_m = combine_split_codes(wb_m, [], ['value','se','ci_lower','ci_upper'])
            wb_parts.append(wb_m)
        wb_ut = pd.concat(wb_parts, ignore_index=True) if wb_parts else wb_ut

    # Also exclude Isles of Scilly from panel
    for df_ref in ['retail_ut', 'base_ut', 'wb_ut']:
        locals()[df_ref] = locals()[df_ref][
            locals()[df_ref]['la_code'] != 'E06000053']

    # Merge retail into base (wide, one row per LA-year)
    print("\n5. Assembling panel...")
    panel = base_ut.merge(
        retail_ut[['la_code', 'year', 'tot', 'tot_new', 'tot_old']],
        on=['la_code', 'year'], how='left'
    )

    # Merge SfC
    panel = panel.merge(
        sfc[['la_code', 'year', 'filled_posts', 'employees',
             'vacant_posts', 'vacancy_rate', 'fte_posts']],
        on=['la_code', 'year'], how='left'
    )

    # Merge wellbeing (long format — expands to 4 rows per LA-year)
    panel = panel.merge(
        wb_ut, on=['la_code', 'year'], how='left'
    )

    panel['nation'] = 'England'

    # Column order
    cols = ['la_code', 'la_name', 'year', 'nation', 'region',
            'measure', 'value', 'se', 'ci_lower', 'ci_upper',
            'tot', 'tot_new', 'tot_old',
            'claimants_december', 'claimants_annual', 'pop_total', 'pop_65plus', 'overseas_share',
            'filled_posts', 'employees', 'vacant_posts',
            'vacancy_rate', 'fte_posts']
    panel = panel[[c for c in cols if c in panel.columns]]
    panel = panel.sort_values(['la_code', 'year', 'measure']).reset_index(drop=True)

    # Summary
    print("\n" + "=" * 60)
    print("ENGLAND SFC PANEL SUMMARY")
    print("=" * 60)
    n_las   = panel['la_code'].nunique()
    n_years = panel['year'].nunique()
    print(f"  LAs:          {n_las}")
    print(f"  Years:        {sorted(panel['year'].unique())}")
    print(f"  Observations: {len(panel):,}")

    print(f"\n  Missing values:")
    key_cols = ['tot', 'claimants_december', 'claimants_annual', 'pop_total', 'overseas_share',
                'filled_posts', 'vacancy_rate', 'value']
    for col in key_cols:
        if col in panel.columns:
            n   = panel[col].isna().sum()
            pct = n / len(panel) * 100
            flag = '  <- check' if pct > 30 else ''
            print(f"    {col:<22} {n:>6} ({pct:5.1f}%){flag}")

    # SfC match rate
    sfc_matched = panel['filled_posts'].notna().sum()
    sfc_total   = len(panel)
    print(f"\n  SfC match rate: {sfc_matched:,}/{sfc_total:,} "
          f"({sfc_matched/sfc_total*100:.1f}%)")

    panel.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Saved: {OUTPUT_FILE}")
    return panel


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()

    print("=" * 60)
    print("ENGLAND SFC PANEL ASSEMBLER")
    print("=" * 60)
    assemble_england_sfc_panel(force_refresh=args.force)
