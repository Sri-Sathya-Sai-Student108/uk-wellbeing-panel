"""
Boundary harmonisation for ONS wellbeing local authority data.

Aggregates predecessor districts up to post-merger geographies using
population-weighted means, so we get a consistent set of LAs across
the full 2011/12 - 2022/23 series.

All mergers during the series:
  2019: BCP, Dorset UA, East Suffolk, West Suffolk, Somerset W&T
  2020: Buckinghamshire UA
  2021: North Northamptonshire, West Northamptonshire
  2023: Cumberland, Westmorland & Furness, North Yorkshire UA, Somerset UA

Note: 2023 mergers post-date the latest wellbeing data (2022-23), so the
entire series uses old district codes. We still aggregate for consistency.
"""

import pandas as pd
import numpy as np

# ---- Merger definitions ----
# new_code -> {name, predecessors (old codes), year of merger}

BOUNDARY_MERGES = {
    # April 2019
    'E06000058': {
        'name': 'Bournemouth, Christchurch and Poole',
        'predecessors': ['E06000028', 'E06000029', 'E07000048'],
        'year': 2019
    },
    'E06000059': {
        'name': 'Dorset',
        'predecessors': ['E07000049', 'E07000050', 'E07000051',
                         'E07000052', 'E07000053'],
        'year': 2019
    },
    'E07000244': {
        'name': 'East Suffolk',
        'predecessors': ['E07000205', 'E07000206'],
        'year': 2019
    },
    'E07000245': {
        'name': 'West Suffolk',
        'predecessors': ['E07000201', 'E07000204'],
        'year': 2019
    },
    'E07000246': {
        'name': 'Somerset West and Taunton',
        'predecessors': ['E07000190', 'E07000191'],
        'year': 2019
    },
    # April 2020
    'E06000060': {
        'name': 'Buckinghamshire',
        'predecessors': ['E07000004', 'E07000005', 'E07000006', 'E07000007'],
        'year': 2020
    },
    # April 2021
    'E06000061': {
        'name': 'North Northamptonshire',
        'predecessors': ['E07000150', 'E07000152', 'E07000153', 'E07000156'],
        'year': 2021
    },
    'E06000062': {
        'name': 'West Northamptonshire',
        'predecessors': ['E07000151', 'E07000154', 'E07000155'],
        'year': 2021
    },
    # April 2023
    'E06000063': {
        'name': 'Cumberland',
        'predecessors': ['E07000026', 'E07000028', 'E07000029'],
        'year': 2023
    },
    'E06000064': {
        'name': 'Westmorland and Furness',
        'predecessors': ['E07000027', 'E07000030', 'E07000031'],
        'year': 2023
    },
    'E06000065': {
        'name': 'North Yorkshire',
        'predecessors': ['E07000163', 'E07000164', 'E07000165',
                         'E07000166', 'E07000167', 'E07000168', 'E07000169'],
        'year': 2023
    },
    'E06000066': {
        'name': 'Somerset',
        'predecessors': ['E07000187', 'E07000188', 'E07000189', 'E07000246'],
        'year': 2023
    },
}

# Mid-2019 population estimates for weighting (approx, from ONS MYE).
POPULATION_WEIGHTS = {
    # BCP predecessors
    'E06000028': 395331, 'E06000029': 151500, 'E07000048': 50530,
    # Dorset predecessors
    'E07000049': 89561, 'E07000050': 71684, 'E07000051': 46800,
    'E07000052': 101700, 'E07000053': 65662,
    # East Suffolk predecessors
    'E07000205': 128082, 'E07000206': 118533,
    # West Suffolk predecessors
    'E07000201': 64588, 'E07000204': 113244,
    # Somerset West and Taunton predecessors
    'E07000190': 117559, 'E07000191': 34675,
    # Buckinghamshire predecessors
    'E07000004': 193113, 'E07000005': 95104,
    'E07000006': 70043, 'E07000007': 174878,
    # Northamptonshire predecessors
    'E07000150': 71200, 'E07000152': 93475,
    'E07000153': 101600, 'E07000156': 79463,
    'E07000151': 84100, 'E07000154': 224610, 'E07000155': 92382,
    # Cumbria predecessors
    'E07000026': 97161, 'E07000028': 108387, 'E07000029': 68424,
    'E07000027': 67037, 'E07000030': 53253, 'E07000031': 104522,
    # North Yorkshire predecessors
    'E07000163': 56832, 'E07000164': 91126, 'E07000165': 160003,
    'E07000166': 53730, 'E07000167': 54920, 'E07000168': 108793,
    'E07000169': 90600,
    # Somerset (2023) predecessors
    'E07000187': 113774, 'E07000188': 122791,
    'E07000189': 167216, 'E07000246': 152000,
}


def harmonise_boundaries(df):
    """
    Aggregate predecessor LAs to merged geography using pop-weighted means.

    For each merger, for years where the new code has no data but
    predecessors do, compute weighted mean and create rows under new code.
    Then drop all predecessor rows.

    Processed chronologically so nested mergers work (Somerset W&T 2019
    feeds into Somerset UA 2023).
    """
    print("\nHarmonising LA boundaries...")
    df = df.copy()
    rows_added = 0

    sorted_merges = sorted(BOUNDARY_MERGES.items(), key=lambda x: x[1]['year'])

    for new_code, info in sorted_merges:
        name = info['name']
        preds = info['predecessors']

        new_years = set(df.loc[df['la_code'] == new_code, 'year'].unique())
        pred_data = df[df['la_code'].isin(preds)]
        pred_years = set(pred_data['year'].unique())
        years_to_fill = pred_years - new_years

        if len(pred_data) == 0 and len(new_years) == 0:
            continue

        n_filled = 0
        if years_to_fill:
            weights = {p: POPULATION_WEIGHTS.get(p, 1) for p in preds}
            new_rows = []

            for year in sorted(years_to_fill):
                for measure in df['measure'].unique():
                    ym = pred_data[
                        (pred_data['year'] == year) &
                        (pred_data['measure'] == measure)
                    ]
                    if len(ym) == 0:
                        continue

                    wsum, wt = 0.0, 0.0
                    for _, row in ym.iterrows():
                        w = weights.get(row['la_code'], 1)
                        if pd.notna(row['value']):
                            wsum += row['value'] * w
                            wt += w

                    if wt > 0:
                        new_rows.append({
                            'la_code': new_code,
                            'la_name': name,
                            'measure': measure,
                            'value': round(wsum / wt, 2),
                            'period': ym['period'].iloc[0],
                            'year': year
                        })

            if new_rows:
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                n_filled = len(new_rows)
                rows_added += n_filled

        n_pred_rows = len(df[df['la_code'].isin(preds)])
        df = df[~df['la_code'].isin(preds)]
        print(f"  {name}: +{n_filled} aggregated, -{n_pred_rows} predecessor rows")

    print(f"  Total rows added: {rows_added}")
    print(f"  Final: {df['la_code'].nunique()} LAs, {len(df)} observations")
    return df


def propagate_classification(class_df):
    """
    Assign area classification to merged LAs from their predecessors.
    If all predecessors share same supergroup, use that.
    If they differ, use the largest predecessor's (by population).
    """
    print("\nPropagating classification to merged LAs...")
    existing = set(class_df['la_code'])
    additions = []

    for new_code, info in BOUNDARY_MERGES.items():
        if new_code in existing:
            continue

        pred_class = class_df[class_df['la_code'].isin(info['predecessors'])]
        if len(pred_class) == 0:
            continue

        sg_col = 'supergroup_code' if 'supergroup_code' in pred_class.columns else 'supergroup'
        unique_sgs = pred_class[sg_col].unique()
        largest = max(info['predecessors'],
                      key=lambda p: POPULATION_WEIGHTS.get(p, 0))
        lg = pred_class[pred_class['la_code'] == largest]

        if len(lg) == 0:
            continue

        row = lg.iloc[0].to_dict()
        row['la_code'] = new_code

        if len(unique_sgs) == 1:
            print(f"  {info['name']}: {row.get('supergroup', '?')}")
        else:
            print(f"  {info['name']}: MIXED {list(unique_sgs)}, "
                  f"assigned {row.get('supergroup', '?')} (largest predecessor)")

        additions.append(row)

    if additions:
        class_df = pd.concat([class_df, pd.DataFrame(additions)],
                             ignore_index=True)
    return class_df


# Scottish LA codes changed after minor boundary revisions.
# The 2011 classification uses old codes; the LAD23 boundaries use new ones.
SCOTTISH_CODE_REMAP = {
    'S12000015': 'S12000047',  # Fife
    'S12000024': 'S12000048',  # Perth and Kinross
    'S12000046': 'S12000049',  # Glasgow City
    'S12000044': 'S12000050',  # North Lanarkshire
}

# Lincolnshire districts were renumbered ~2019
# Old codes (E07000032-039) now refer to Derbyshire in LAD23
# New codes (E07000136-142) are the current Lincolnshire codes
LINCOLNSHIRE_CODE_REMAP = {
    'E07000032': 'E07000136',  # Boston
    'E07000033': 'E07000137',  # East Lindsey
    'E07000034': 'E07000138',  # Lincoln
    'E07000035': 'E07000139',  # North Kesteven
    'E07000036': 'E07000140',  # South Holland
    'E07000037': 'E07000141',  # South Kesteven
    'E07000038': 'E07000142',  # West Lindsey
}


def remap_scottish_codes(df, code_col='la_code'):
    """
    Update old Scottish LA codes to current LAD23 codes, and fix
    other known code issues in the classification file.
    Apply to both wellbeing data and classification data so they
    match the LAD23 boundary file.
    """
    df = df.copy()

    # Scottish code changes
    df[code_col] = df[code_col].replace(SCOTTISH_CODE_REMAP)

    # Cornwall / Isles of Scilly ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â classification file has them as
    # "E06000052/E06000053" in one row. Split into two rows.
    combined = df[df[code_col] == 'E06000052/E06000053']
    if len(combined) > 0:
        cornwall = combined.copy()
        cornwall[code_col] = 'E06000052'
        scilly = combined.copy()
        scilly[code_col] = 'E06000053'
        df = df[df[code_col] != 'E06000052/E06000053']
        df = pd.concat([df, cornwall, scilly], ignore_index=True)

    return df


# ---- County Split definitions ----
# Counties that were abolished and replaced by multiple unitaries
# We combine these BACK to original county footprint to maintain panel balance

BOUNDARY_SPLITS = {
    'DORSET_COMBINED': {
        'name': 'Dorset (combined)',
        'split_parts': ['E06000058', 'E06000059'],  # BCP + Dorset UA
        'year': 2019,
        'original': 'Dorset county'
    },
    'NORTHANTS_COMBINED': {
        'name': 'Northamptonshire (combined)',
        'split_parts': ['E06000061', 'E06000062'],  # North + West
        'year': 2021,
        'original': 'Northamptonshire county'
    },
    'CUMBRIA_COMBINED': {
        'name': 'Cumbria (combined)',
        'split_parts': ['E06000063', 'E06000064'],  # Cumberland + Westmorland & Furness
        'year': 2023,
        'original': 'Cumbria county'
    }
}

# Manual classification override for combined county splits
# Used when split parts have MIXED classifications and "largest by population"
# would assign an inappropriate classification
SPLIT_CLASSIFICATIONS = {
    'DORSET_COMBINED': {
        'supergroup': 'Countryside Living',
        'group': 'English and Welsh Countryside',
        'rationale': 'Predominantly rural despite BCP urban area'
    },
    'NORTHANTS_COMBINED': {
        'supergroup': 'Urban Settlements',
        'group': 'Manufacturing Traits',
        'rationale': 'Mix of urban (Northampton, Kettering, Corby) and market towns'
    },
    'CUMBRIA_COMBINED': {
        'supergroup': 'Countryside Living',
        'group': 'English and Welsh Countryside',
        'rationale': 'Overwhelmingly rural (Lake District) despite Barrow industrial legacy'
    }
}


def combine_splits(df):
    """
    Combine county split parts back to original county footprint.
    
    Three counties were abolished and replaced by multiple unitaries:
    - Dorset (2019) -> BCP + Dorset UA
    - Northamptonshire (2021) -> North + West
    - Cumbria (2023) -> Cumberland + Westmorland & Furness
    
    ONS publishes these split codes with only partial backfilled data.
    We combine them back to maintain a balanced 12-year panel.
    
    Uses equal-weighted aggregation (simple mean) since split parts
    represent non-overlapping subdivisions with similar populations.
    """
    print("\nCombining county splits to maintain balanced panel...")
    df = df.copy()
    rows_added = 0
    
    for combined_code, info in BOUNDARY_SPLITS.items():
        split_parts = info['split_parts']
        name = info['name']
        
        # Check if any split parts exist in the data
        parts_data = df[df['la_code'].isin(split_parts)]
        if len(parts_data) == 0:
            print(f"  {name}: No split parts found in data")
            continue
        
        # Check if combined code already exists
        if combined_code in df['la_code'].values:
            print(f"  {name}: Already combined, skipping")
            continue
        
        # Group by year and measure, compute equal-weighted mean
        if 'measure' in df.columns:
            # Wellbeing data format
            grouped = parts_data.groupby(['year', 'measure']).agg({
                'value': 'mean',  # Equal-weighted mean
                'period': 'first'
            }).reset_index()
            grouped['la_code'] = combined_code
            grouped['la_name'] = name
            
            # Reorder columns to match input
            cols = ['la_code', 'la_name', 'measure', 'value', 'period', 'year']
            grouped = grouped[[c for c in cols if c in grouped.columns]]
            
        else:
            # Classification data format
            # Use manual override if available, otherwise take first split part
            if combined_code in SPLIT_CLASSIFICATIONS:
                override = SPLIT_CLASSIFICATIONS[combined_code]
                first_part = df[df['la_code'] == split_parts[0]].copy()
                if len(first_part) > 0:
                    # Take structure from first part but override key fields
                    first_part['la_code'] = combined_code
                    if 'la_name' in first_part.columns:
                        first_part['la_name'] = name
                    if 'supergroup' in first_part.columns:
                        first_part['supergroup'] = override['supergroup']
                    if 'group' in first_part.columns and 'group' in override:
                        first_part['group'] = override['group']
                    grouped = first_part
                    print(f"  {name}: assigned {override['supergroup']} (manual override - {override['rationale']})")
                else:
                    print(f"  {name}: No data for first split part")
                    continue
            else:
                # Fallback: just take first split part's classification
                first_part = df[df['la_code'] == split_parts[0]].copy()
                if len(first_part) > 0:
                    first_part['la_code'] = combined_code
                    if 'la_name' in first_part.columns:
                        first_part['la_name'] = name
                    grouped = first_part
                else:
                    print(f"  {name}: No data for first split part")
                    continue
        
        # Add combined rows
        df = pd.concat([df, grouped], ignore_index=True)
        rows_added += len(grouped)
        
        # Remove the split parts
        n_removed = len(df[df['la_code'].isin(split_parts)])
        df = df[~df['la_code'].isin(split_parts)]
        
        print(f"  {name}: +{len(grouped)} combined rows, -{n_removed} split part rows")
    
    n_las = df['la_code'].nunique() if 'la_code' in df.columns else 0
    print(f"  Total rows added: {rows_added}")
    print(f"  Final: {n_las} LAs")
    
    return df
