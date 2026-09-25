"""
Data loading functions for wellbeing and area classification data.
"""

import pandas as pd
import numpy as np
import os
import sys
from config import DATA_DIR, SUPERGROUP_NAMES, GROUP_NAMES


def check_data_files():
    """Check required files exist and guide user if not."""
    files = {
        'wellbeing': (
            os.path.join(DATA_DIR, 'wellbeing_la.csv'),
            'https://download.ons.gov.uk/downloads/datasets/'
            'wellbeing-local-authority/editions/time-series/versions/4.csv'
        ),
        'classification': (
            os.path.join(DATA_DIR, 'cluster_membership.xls'),
            'https://www.ons.gov.uk/file?uri=/methodology/geography/'
            'geographicalproducts/areaclassifications/'
            '2011areaclassifications/datasets/clustermembershipv2.xls'
        ),
    }

    missing = {k: v for k, v in files.items() if not os.path.exists(v[0])}
    if missing:
        print("=" * 70)
        print("MISSING DATA FILES - please download:\n")
        for name, (path, url) in missing.items():
            print(f"  {name}:")
            print(f"    URL:  {url}")
            print(f"    Save: {path}\n")
        return False
    return True


def load_wellbeing_data():
    """
    Load ONS wellbeing local authority CSV.

    Returns DataFrame with columns:
      la_code, la_name, measure, value, period, year, se, ci_lower, ci_upper
      
    Standard errors (se) extracted from confidence intervals for precision weighting:
      se = (ci_upper - ci_lower) / (2 Ã— 1.96)
    """
    filepath = os.path.join(DATA_DIR, 'wellbeing_la.csv')
    print(f"Loading wellbeing data from {filepath}...")

    df = pd.read_csv(filepath, low_memory=False)
    df.columns = (df.columns.str.lower()
                  .str.replace(' ', '_').str.replace('-', '_'))

    # Auto-detect columns
    col_map = {}
    for target, candidates in {
        'geo': ['administrative_geography', 'geography_code', 'area_code'],
        'name': ['geography', 'area_name', 'geography_name'],
        'measure': ['measureofwellbeing', 'measure_of_wellbeing'],
        'time': ['time', 'date', 'period'],
        'value': ['v4_1', 'v4_3', 'v4_0', 'observation', 'value'],
        'estimate': ['estimate', 'estimate_type', 'wellbeing_estimate'],
    }.items():
        for c in candidates:
            if c in df.columns:
                col_map[target] = c
                break

    for r in ['geo', 'measure', 'time', 'value']:
        if r not in col_map:
            print(f"ERROR: Can't find '{r}'. Columns: {list(df.columns)}")
            sys.exit(1)

    # Filter to mean estimates
    if 'estimate' in col_map:
        df = df[df[col_map['estimate']].str.contains(
            'mean|average', case=False, na=False)]

    # Filter to LA-level codes only
    df = df[df[col_map['geo']].str.match(
        r'^(E0[6-9]|W06|S12|N09)', na=False)]

    df[col_map['value']] = pd.to_numeric(df[col_map['value']], errors='coerce')
    df['year'] = df[col_map['time']].str[:4].astype(int)

    # Extract standard errors from confidence intervals if available
    # CI width = upper - lower Ã¢â€°Ë† 2 Ãƒâ€” 1.96 Ãƒâ€” SE for 95% CI
    lower_cols = [c for c in df.columns if 'lower' in c.lower() and 'limit' in c.lower()]
    upper_cols = [c for c in df.columns if 'upper' in c.lower() and 'limit' in c.lower()]
    
    if lower_cols and upper_cols:
        df['ci_lower'] = pd.to_numeric(df[lower_cols[0]], errors='coerce')
        df['ci_upper'] = pd.to_numeric(df[upper_cols[0]], errors='coerce')
        df['se'] = (df['ci_upper'] - df['ci_lower']) / (2 * 1.96)
        # Set negative or zero SEs to NaN (invalid)
        df.loc[df['se'] <= 0, 'se'] = np.nan
        print(f"  Extracted standard errors from CIs ({df['se'].notna().sum()} valid)")
    else:
        print(f"  Warning: Could not find CI columns, SEs not available")

    rename = {col_map['geo']: 'la_code', col_map['measure']: 'measure',
              col_map['value']: 'value', col_map['time']: 'period'}
    if 'name' in col_map:
        rename[col_map['name']] = 'la_name'
    df = df.rename(columns=rename)
    df['measure'] = df['measure'].str.lower().str.replace(' ', '-')

    keep = ['la_code', 'measure', 'value', 'period', 'year']
    if 'la_name' in df.columns:
        keep.insert(1, 'la_name')
    if 'se' in df.columns:
        keep.append('se')
        keep.append('ci_lower')
        keep.append('ci_upper')
    df = df[keep].copy()

    print(f"  {len(df)} obs, {df['la_code'].nunique()} LAs, "
          f"years {df['year'].min()}-{df['year'].max()}")
    return df


def load_area_classification():
    """
    Load ONS 2011 Area Classification for Local Authorities.

    Returns DataFrame with: la_code, supergroup_code, supergroup,
    and optionally group_code, group.
    """
    filepath = os.path.join(DATA_DIR, 'cluster_membership.xls')
    print(f"\nLoading area classification from {filepath}...")

    # First, list all sheets so we can find the right one
    try:
        xls = pd.ExcelFile(filepath)
        print(f"  Sheets available: {xls.sheet_names}")
    except Exception as e:
        print(f"  Could not list sheets: {e}")

    # The XLS often has title rows before the actual data header.
    # Try different sheet names and skip rows until we find the LA-level data.
    # We need a sheet with individual LA codes (E06..., E07... etc), not summaries.
    df = None
    for sheet in xls.sheet_names:
        for skip in [8, 7, 6, 5, 4, 3, 2, 1, 0]:
            try:
                trial = pd.read_excel(filepath, sheet_name=sheet,
                                      skiprows=skip)
                # Check if this sheet has LA-level codes (need > 50 rows 
                # with E/W/S/N codes to distinguish from summary sheets)
                for c in trial.columns[:5]:
                    vals = trial[c].dropna().astype(str)
                    n_la_codes = vals.str.match(r'^[EWSN]\d{2}\d{5}').sum()
                    if n_la_codes > 50:
                        df = trial
                        print(f"  Using sheet='{sheet}', skiprows={skip} "
                              f"({n_la_codes} LA codes found)")
                        break
                if df is not None:
                    break
            except Exception:
                continue
        if df is not None:
            break

    if df is None or len(df) < 10:
        print("ERROR: Could not read classification file.")
        print("  Try opening the XLS and checking the layout.")
        sys.exit(1)

    df.columns = [str(c).strip() for c in df.columns]

    # If columns are all 'Unnamed', the real header is the first data row
    # (common with merged cells in ONS Excel files)
    if all('unnamed' in str(c).lower() for c in df.columns):
        print("  Columns unnamed ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â using first data row as header...")
        new_cols = [str(v).strip() if pd.notna(v) else f'col_{i}'
                    for i, v in enumerate(df.iloc[0])]
        df.columns = new_cols
        df = df.iloc[1:].reset_index(drop=True)
        print(f"  Recovered columns: {list(df.columns)}")
    print(f"  Columns: {list(df.columns)}")

    # Auto-detect columns by name.
    # The file has: Code, Name, Region/Country, Supergroup Code,
    # Supergroup Name, Group Code, Group Name, Subgroup Code, Subgroup Name
    code_col = sg_code_col = sg_name_col = None
    grp_code_col = grp_name_col = None
    sub_code_col = sub_name_col = None

    for c in df.columns:
        cl = c.lower()
        if cl == 'code' or (cl.endswith('code') and 'group' not in cl
                            and 'sub' not in cl and 'super' not in cl):
            code_col = c
        elif 'supergroup' in cl and 'code' in cl:
            sg_code_col = c
        elif 'supergroup' in cl and 'name' in cl:
            sg_name_col = c
        elif 'subgroup' in cl and 'code' in cl:
            sub_code_col = c
        elif 'subgroup' in cl and 'name' in cl:
            sub_name_col = c
        elif 'group' in cl and 'code' in cl and 'super' not in cl and 'sub' not in cl:
            grp_code_col = c
        elif 'group' in cl and 'name' in cl and 'super' not in cl and 'sub' not in cl:
            grp_name_col = c

    if not code_col:
        for c in df.columns:
            if df[c].dropna().astype(str).str.match(r'^[EWSN]\d{2}\d{5}').any():
                code_col = c
                break

    if not code_col or not (sg_code_col or sg_name_col):
        print("  Auto-detect by name failed, trying positional detection...")
        for c in df.columns:
            vals = df[c].dropna().astype(str)
            if code_col is None and vals.str.match(r'^[EWSN]\d').any():
                code_col = c
            elif sg_code_col is None and vals.str.match(r'^[1-8]r?$').mean() > 0.5:
                sg_code_col = c

    if not code_col or not (sg_code_col or sg_name_col):
        print(f"ERROR: Can't find columns. Available: {list(df.columns)}")
        print(f"  First few rows:\n{df.head()}")
        sys.exit(1)

    # Build result using name columns directly where available,
    # falling back to code-based mapping
    result = pd.DataFrame({
        'la_code': df[code_col].astype(str).str.strip(),
    })

    if sg_name_col:
        result['supergroup'] = df[sg_name_col].astype(str).str.strip()
    if sg_code_col:
        result['supergroup_code'] = (df[sg_code_col].astype(str)
                                     .str.strip().str.replace('r', ''))
        if sg_name_col is None:
            result['supergroup'] = result['supergroup_code'].map(SUPERGROUP_NAMES)

    if grp_name_col:
        result['group'] = df[grp_name_col].astype(str).str.strip()
    if grp_code_col:
        result['group_code'] = (df[grp_code_col].astype(str)
                                .str.strip().str.replace('r', ''))
        if grp_name_col is None:
            result['group'] = result['group_code'].map(GROUP_NAMES)

    if sub_name_col:
        result['subgroup'] = df[sub_name_col].astype(str).str.strip()
    if sub_code_col:
        result['subgroup_code'] = (df[sub_code_col].astype(str)
                                   .str.strip().str.replace('r', ''))

    result = result[result['la_code'].str.match(r'^[EWSN]', na=False)]

    # Report what we found
    levels = []
    if 'supergroup' in result.columns:
        levels.append(f"{result['supergroup'].nunique()} supergroups")
    if 'group' in result.columns:
        levels.append(f"{result['group'].dropna().nunique()} groups")
    if 'subgroup' in result.columns:
        levels.append(f"{result['subgroup'].dropna().nunique()} subgroups")
    print(f"  {len(result)} LAs classified ({', '.join(levels)})")
    return result
