#!/usr/bin/env python3
"""
scotland_panel.py - Assembles the Scotland local authority panel.

Produces:
  data/intermediate/scotland_panel.csv

Columns: la_code, la_name, year, tot, tot_new, tot_old,
         claimants_december, claimants_annual, pop_total, pop_65plus,
         vacancy_rate

Builds the FULL 32-council panel -- island authorities (Orkney,
Shetland, Na h-Eileanan Siar) are NOT excluded here. Per the same
convention as England (City of London/Isles of Scilly are excluded in
bartik_check.py's load_data(), not in assemble_england.py), exclusions
belong at the analysis stage, not baked permanently into the base
panel. This keeps the assembled file reusable for other purposes.
See check_scotland_bartik.py for where the island exclusion is applied
for the Bartik/IV analysis specifically.

Retail: years 2016-2023 (full range, same as England)
Claimants/population: years 2016-2023 (full range, same as England)
vacancy_rate: years 2020-2023 ONLY (SSSC source constraint -- see
  README.SCOT Section 1). Rows for other years have vacancy_rate = NaN.

vacancy_rate source: combined from three SSSC/Care Inspectorate
publications, cross-validated against each other for every overlapping
year (exact match, no revisions found -- see README.SCOT):
  - 2020: "Staff vacancies in care services 2022" report PDF, Table 1j
    (2022-vintage report; pre-2023 reports have no companion
    spreadsheet, so this year's figures are transcribed directly from
    the PDF's own embedded table text -- not machine-parsed)
  - 2021, 2022: "...2023 supporting tables" (data_tables_2023.xlsx),
    Table 1j
  - 2023: "...2024 supporting tables" (data_tables_2024.xlsx), Table 1j
    (most recent vintage available for this year)

SSSC scope limitation (documented, not fixed -- see README.SCOT
Section 1): this covers ALL social services (children, young people,
adults, older people combined), not adult-only like England's Skills
for Care data. No LA-level age-group breakdown exists in this source.

Usage:
  python scotland_panel.py [--force]
"""

import argparse
import os

import numpy as np
import pandas as pd

from config import DATA_DIR

INTERMEDIATE = os.path.join(DATA_DIR, 'intermediate')
OUTPUT_FILE = os.path.join(INTERMEDIATE, 'scotland_panel.csv')

RETAIL_SCOTLAND_FILE = os.path.join(INTERMEDIATE, 'retail_data_scotland.csv')
CLAIMANTS_FILE = os.path.join(INTERMEDIATE, 'claimant_count_annual.csv')
POP_FILE = os.path.join(INTERMEDIATE, 'population_annual.csv')

YEAR_MIN = 2016
YEAR_MAX = 2023


# ---------------------------------------------------------------------------
# SSSC LA name -> S12000 code mapping
# ---------------------------------------------------------------------------
# SSSC tables use short-form names for 6 councils that differ from the
# project's standard la_name (as confirmed against claimant_count_annual.csv
# S-code rows). The remaining 26 councils match exactly.
SSSC_NAME_TO_CODE = {
    'Aberdeen':             'S12000033',  # SSSC "Aberdeen" -> "Aberdeen City"
    'Aberdeenshire':        'S12000034',
    'Angus':                'S12000041',
    'Argyll and Bute':      'S12000035',
    'Clackmannanshire':     'S12000005',
    'Dumfries and Galloway':'S12000006',
    'Dundee':               'S12000042',  # SSSC "Dundee" -> "Dundee City"
    'East Ayrshire':        'S12000008',
    'East Dunbartonshire':  'S12000045',
    'East Lothian':         'S12000010',
    'East Renfrewshire':    'S12000011',
    'Edinburgh':            'S12000036',  # SSSC "Edinburgh" -> "City of Edinburgh"
    'Falkirk':              'S12000014',
    'Fife':                 'S12000047',
    'Glasgow':              'S12000049',  # SSSC "Glasgow" -> "Glasgow City"
    'Highland':             'S12000017',
    'Inverclyde':           'S12000018',
    'Midlothian':           'S12000019',
    'Moray':                'S12000020',
    'Na h-Eileanan Siar':   'S12000013',
    'North Ayrshire':       'S12000021',
    'North Lanarkshire':    'S12000050',
    'Orkney':               'S12000023',  # SSSC "Orkney" -> "Orkney Islands"
    'Perth and Kinross':    'S12000048',
    'Renfrewshire':         'S12000038',
    'Scottish Borders':     'S12000026',
    'Shetland':             'S12000027',  # SSSC "Shetland" -> "Shetland Islands"
    'South Ayrshire':       'S12000028',
    'South Lanarkshire':    'S12000029',
    'Stirling':             'S12000030',
    'West Dunbartonshire':  'S12000039',
    'West Lothian':         'S12000040',
}


# ---------------------------------------------------------------------------
# SSSC vacancy_rate data, 2020-2023
# ---------------------------------------------------------------------------
# 2020 figures transcribed directly from the "Staff vacancies in care
# services 2022" report PDF's Table 1j (no companion spreadsheet exists
# for this vintage -- see docstring above). Cross-validated: the same
# PDF's 2021 and 2022 columns match the 2023/2024 supporting-tables
# files exactly (spot-checked Aberdeen, Edinburgh, Orkney -- see
# README.SCOT), giving confidence in this transcription.
VACANCY_RATE_2020 = {
    'Aberdeen': 0.068, 'Aberdeenshire': 0.041, 'Angus': 0.028,
    'Argyll and Bute': 0.061, 'Clackmannanshire': 0.065,
    'Dumfries and Galloway': 0.042, 'Dundee': 0.061,
    'East Ayrshire': 0.046, 'East Dunbartonshire': 0.031,
    'East Lothian': 0.069, 'East Renfrewshire': 0.039,
    'Edinburgh': 0.066, 'Falkirk': 0.058, 'Fife': 0.052,
    'Glasgow': 0.049, 'Highland': 0.049, 'Inverclyde': 0.057,
    'Midlothian': 0.052, 'Moray': 0.058, 'Na h-Eileanan Siar': 0.053,
    'North Ayrshire': 0.037, 'North Lanarkshire': 0.048,
    'Orkney': 0.048, 'Perth and Kinross': 0.067,
    'Renfrewshire': 0.050, 'Scottish Borders': 0.058,
    'Shetland': 0.060, 'South Ayrshire': 0.036,
    'South Lanarkshire': 0.036, 'Stirling': 0.049,
    'West Dunbartonshire': 0.062, 'West Lothian': 0.043,
}


def load_vacancy_rate():
    """
    Combine SSSC vacancy_rate for 2020-2023 from the three available
    sources: 2020 hardcoded from the 2022-vintage PDF (see
    VACANCY_RATE_2020 above), 2021/2022/2023 parsed from whichever
    xlsx supporting-tables file is the most recent available for that
    year (2023 file for 2021, 2024 file for 2022 and 2023 -- though
    all overlapping years have been confirmed identical across
    vintages, so this preference is precautionary, not corrective).

    NOTE: file paths below assume the SSSC source files are saved at
    data/sssc/ -- adjust if saved elsewhere.
    """
    rows = []

    # 2020 -- hardcoded from 2022 PDF (no parseable source exists)
    for name, rate in VACANCY_RATE_2020.items():
        rows.append({'la_name_sssc': name, 'year': 2020, 'vacancy_rate': rate})

    # 2021, 2022 -- from 2023 supporting tables (Table 1j gives
    # 2023/2022/2021 columns; we take 2021 and 2022 from here, and let
    # the 2024 file override 2022/2023)
    sssc_2023_path = os.path.join(DATA_DIR, 'sssc',
                                   'staff_vacancies_in_care_services_data_tables_2023.xlsx')
    if os.path.exists(sssc_2023_path):
        rows.extend(_parse_table_1j(sssc_2023_path, years_to_keep=[2021, 2022]))
    else:
        print(f"  WARNING: {sssc_2023_path} not found -- 2021/2022 vacancy_rate "
              f"will be missing unless the 2024 file covers them.")

    # 2022, 2023 -- from 2024 supporting tables (most recent vintage;
    # overrides 2022 from the 2023 file above, since dict-based merge
    # below takes the last value written per (la_name_sssc, year))
    sssc_2024_path = os.path.join(DATA_DIR, 'sssc',
                                   'staff_vacancies_in_care_services_data_tables_2024.xlsx')
    if os.path.exists(sssc_2024_path):
        rows.extend(_parse_table_1j(sssc_2024_path, years_to_keep=[2022, 2023]))
    else:
        print(f"  WARNING: {sssc_2024_path} not found -- 2023 vacancy_rate "
              f"will be missing, and 2022 will only come from the 2023 file.")

    df = pd.DataFrame(rows)

    # Most-recent-vintage-wins for any (la_name, year) appearing twice
    # (2022 appears in both the 2023 and 2024 file parses above).
    # Precautionary only -- confirmed identical across vintages.
    df = df.drop_duplicates(subset=['la_name_sssc', 'year'], keep='last')

    df['la_code'] = df['la_name_sssc'].map(SSSC_NAME_TO_CODE)
    unmatched = df[df['la_code'].isna()]['la_name_sssc'].unique()
    if len(unmatched) > 0:
        print(f"  WARNING: {len(unmatched)} SSSC LA names did not match "
              f"the S12000 code mapping: {list(unmatched)}")

    return df[['la_code', 'year', 'vacancy_rate']].dropna(subset=['la_code'])


def _parse_table_1j(xlsx_path, years_to_keep):
    """
    Extract Table 1j (vacancy_rate by LA area) from an SSSC supporting-
    tables workbook. Locates the table by searching for its title text
    rather than a fixed row number, since row position has shifted
    slightly between the 2023 and 2024 vintages (69 vs 72) -- searching
    is more robust to further layout drift than hardcoding an offset.
    """
    wb_sheet = 'Tables1g-1k'
    xl = pd.ExcelFile(xlsx_path)
    if wb_sheet not in xl.sheet_names:
        print(f"  WARNING: sheet '{wb_sheet}' not found in {xlsx_path}. "
              f"Actual sheets: {xl.sheet_names}")
        return []

    raw = xl.parse(wb_sheet, header=None)
    title_matches = raw[raw[0].astype(str).str.contains('Table 1j', na=False)]
    if len(title_matches) == 0:
        print(f"  WARNING: 'Table 1j' not found in {xlsx_path} sheet {wb_sheet}")
        return []
    start_row = title_matches.index[0]

    # Year header row is 3 rows below the title (title, blank, column
    # group labels, year labels) -- confirmed structure in both 2023
    # and 2024 vintages.
    year_row = raw.iloc[start_row + 3]
    # Columns 1-3 are "Total services with WTE data" for 3 years,
    # columns 4-6 are "Rate of WTE vacancies" for the SAME 3 years, in
    # the same order.
    years_in_file = [int(year_row[c]) for c in [4, 5, 6]]

    rows = []
    r = start_row + 4
    while True:
        row = raw.iloc[r]
        name = row[0]
        if name is None or 'Grand total' in str(name) or pd.isna(name):
            break
        for i, yr in enumerate(years_in_file):
            if yr in years_to_keep:
                rows.append({
                    'la_name_sssc': str(name).strip(),
                    'year': yr,
                    'vacancy_rate': row[4 + i],
                })
        r += 1

    return rows


def build_panel(force_refresh=False):
    if os.path.exists(OUTPUT_FILE) and not force_refresh:
        print(f"  Loading cached Scotland panel from {OUTPUT_FILE}...")
        return pd.read_csv(OUTPUT_FILE)

    print("Building Scotland panel...")

    retail = pd.read_csv(RETAIL_SCOTLAND_FILE)
    print(f"  Retail: {retail['la_code'].nunique()} councils, "
          f"years {retail['year'].min()}-{retail['year'].max()}")

    claimants = pd.read_csv(CLAIMANTS_FILE)
    claimants = claimants[claimants['la_code'].str.startswith('S', na=False)].copy()
    print(f"  Claimants: {claimants['la_code'].nunique()} councils")

    pop = pd.read_csv(POP_FILE)
    pop = pop[pop['la_code'].str.startswith('S', na=False)].copy()
    print(f"  Population: {pop['la_code'].nunique()} councils")

    needed_pop_cols = ['la_code', 'year', 'pop_total', 'pop_65plus']
    missing = [c for c in needed_pop_cols if c not in pop.columns]
    if missing:
        raise ValueError(
            f"population_annual.csv missing expected columns {missing}. "
            f"Actual columns: {pop.columns.tolist()}. Check column names "
            f"before proceeding -- do not guess.")

    needed_claimant_cols = ['la_code', 'year', 'claimants_december',
                             'claimants_annual']
    missing_cc = [c for c in needed_claimant_cols if c not in claimants.columns]
    if missing_cc:
        raise ValueError(
            f"claimant_count_annual.csv missing expected columns "
            f"{missing_cc}. Actual columns: {claimants.columns.tolist()}.")

    panel = retail[['la_code', 'la_name', 'year', 'tot', 'tot_new', 'tot_old']].copy()
    panel = panel.merge(claimants[needed_claimant_cols], on=['la_code', 'year'],
                         how='left')
    panel = panel.merge(pop[needed_pop_cols], on=['la_code', 'year'], how='left')

    vacancy = load_vacancy_rate()
    print(f"  Vacancy rate: {vacancy['la_code'].nunique()} councils, "
          f"years {sorted(vacancy['year'].unique())}")
    panel = panel.merge(vacancy, on=['la_code', 'year'], how='left')

    panel = panel[panel['year'].between(YEAR_MIN, YEAR_MAX)].copy()

    n_councils = panel['la_code'].nunique()
    n_years = panel['year'].nunique()
    print(f"\n  Panel: {n_councils} councils x {n_years} years = "
          f"{len(panel)} rows")
    print(f"  vacancy_rate populated for "
          f"{panel['vacancy_rate'].notna().sum()} of {len(panel)} rows "
          f"(expected: only 2020-2023)")

    for col in ['claimants_december', 'claimants_annual', 'pop_total',
                'pop_65plus']:
        n_missing = panel[col].isna().sum()
        if n_missing > 0:
            print(f"  WARNING: {col} missing for {n_missing} rows")

    panel.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Saved: {OUTPUT_FILE}")
    return panel


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true',
                         help='Force rebuild even if cached file exists')
    args = parser.parse_args()
    build_panel(force_refresh=args.force)
