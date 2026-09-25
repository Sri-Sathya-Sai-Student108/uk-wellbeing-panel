# Project Specification: QOF Practice-Level to Local Authority Prevalence Pipeline

## Objective

Build a reusable Python pipeline that converts NHS QOF (Quality and Outcomes Framework) practice-level prevalence data into a longitudinal panel dataset at lower-tier local authority level for England, covering 2012/13 to 2022/23.

The output is a single CSV: `la_code, year, condition, prevalence_pct, n_practices, register_total, list_size_total`

This plugs directly into the wellbeing trajectory project's `qof_panel.py` fixed effects model.

## Why this is needed

- QOF practice-level data is published annually by NHS Digital but has never been systematically aggregated to lower-tier LA level across the full time series
- Fingertips publishes QOF prevalence at UTLA level (counties + unitaries), which misses ~160 district councils and halves the usable sample
- No curated longitudinal LA-level QOF dataset exists publicly
- This is potentially a publishable data descriptor paper in its own right

## Data inputs

### 1. QOF practice-level prevalence files (11 years)

One file per year from the NHS Digital QOF publication series. The file format changed over the years:

| Period | Format | Notes |
|--------|--------|-------|
| 2012-13 to 2014-15 | XLSX, separate file per indicator group | Cardiovascular group file needed. Multiple sheets. Header rows vary. |
| 2015-16 to 2018-19 | CSV or XLSX, separate per group | More standardised. Practice code + indicator code + register + list size. |
| 2019-20 onwards | Raw data CSV zip available | Single zip contains all groups. Filter for indicator of interest. |
| 2020-21 | Prevalence only (COVID payment protection) | Achievement data unreliable but prevalence registers still published. |
| 2021-22 | Payment protection continued | Same caveat as 2020-21. |

Publication landing page for all years:
https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data

Each year's page has a URL like:
- Pre-2019: `.../quality-and-outcomes-framework-qof-YYYY-YY`
- 2019 onwards: `.../YYYY-YY`

### 2. GP practice to postcode lookup (epraccur)

Maps each GP practice code to its premises postcode. Published by the NHS Organisation Data Service.

- Old CSV downloads retired September 2025
- Now available via Data Search and Export (DSE): https://www.odsdatasearchandexport.nhs.uk/
- Search for "epraccur" predefined report
- Also accessible from: https://digital.nhs.uk/services/organisation-data-service/data-search-and-export/csv-downloads/gp-and-gp-practice-related-data
- DSE reports are dynamic (update nightly) and include records closed since 31 March 2017
- Key columns: practice code (col 0), postcode (col 9), status

### 3. Postcode to LA lookup (NSPL)

Maps UK postcodes to lower-tier local authority codes. Published quarterly by ONS Geography.

- Download from: https://www.data.gov.uk/dataset/7ec10db7-c8f4-4a40-8d82-8921935b4865/national-statistics-postcode-lookup-uk
- Or: https://geoportal.statistics.gov.uk (search "NSPL")
- ~178MB zip, main CSV in the Data folder
- Key columns: pcds (postcode), laua (lower-tier LA code)
- Use the version closest to the middle of the study period, or multiple versions

## Processing pipeline

### Step 1: Build practice → LA lookup

```
epraccur (practice_code → postcode)
    + NSPL (postcode → la_code)
    = lookup (practice_code → la_code)
```

- Clean postcodes: strip spaces, uppercase
- Filter epraccur to valid practice codes (letter + 5 digits, e.g. A81001)
- Join on cleaned postcode
- Expect ~95%+ match rate

### Step 2: Parse each year's QOF file

For each year:
- Load the practice-level file (CSV or XLSX)
- Find the relevant columns: practice_code, indicator_code, register_count, list_size
- Filter to the target condition (e.g. HYP001 for hypertension)
- Handle format variations across years (see challenges below)

Target conditions (stable across the full period):
- **HYP001**: Hypertension register (all ages) — recommended primary indicator
- **DM001**: Diabetes register (17+) — recommended sensitivity check
- Other stable registers: ASTHMA, CHD, COPD, EPILEPSY, CANCER

### Step 3: Aggregate to LA

For each year:
```
Join practice data to lookup on practice_code
Group by la_code:
    prevalence = sum(register) / sum(list_size) * 100
    n_practices = count(practices)
```

List-size weighting is implicit in this aggregation — larger practices contribute more to the LA prevalence, which is correct.

### Step 4: Output

Concatenate all years into a single panel CSV:
```
la_code, year, qof_prevalence, n_practices, register_total, list_size_total
E07000026, 2012, 15.3, 12, 8234, 53821
E07000026, 2013, 15.5, 12, 8401, 54192
...
```

## Key challenges

### File format variation
The QOF files changed format significantly across the period. The parser needs to handle:
- XLSX with multiple sheets and header rows (2012-15)
- CSV with varying column names (2015-19)
- Raw data zip containing all indicators (2019+)
- Long format (one row per practice per indicator) vs wide format (one row per practice, columns per indicator)

Recommendation: write a separate parser function per era, with a dispatcher that detects the format.

### Column name variation
Practice code columns have been called: `Practice code`, `PRACTICE_CODE`, `Org_Code`, `Organisation_Code`, etc.
Register columns: `Register`, `Numerator`, `Prevalence_Numerator`, `HYP_REG`, etc.
List size columns: `List_Size`, `List_Size_All`, `Field4`, etc.

Recommendation: use fuzzy matching on column names plus positional fallback.

### Practice to LA mapping over time
- Some practices open/close during the period
- Practice postcodes occasionally change
- The epraccur from DSE is current state, not historical
- For a robust approach, use the TRUD ODS weekly packs for historical practice data
- For a pragmatic first pass, the current epraccur covers most practices that were active during 2012-2023

### Boundary changes
The wellbeing project already handles LA boundary mergers (2019-2023). The QOF pipeline should output data using whatever LA codes the postcode lookup produces. The wellbeing project's boundary harmonisation then handles the rest when the two datasets are merged.

### Cross-boundary registration
Patients don't always register at a GP in their LA of residence. The practice-postcode approach assigns prevalence to the LA where the practice is located, not where patients live. This is standard in the literature and works well at LA level. The LSOA-based approach (as used by the House of Commons Library) is more precise but much more complex.

## Validation

- Compare output against Fingertips UTLA-level data for the same years — the aggregated prevalences should be close for unitary authorities (where UTLA = lower-tier LA)
- Check that national prevalence matches NHS Digital published figures
- Check for outlier LAs with implausibly high/low prevalence
- Report the practice match rate (% of QOF practices matched to an LA)

## Potential as a standalone publication

"A longitudinal dataset of primary care disease prevalence at local authority level in England, 2012–2023"

Suitable for: BMJ Open data descriptor, Scientific Data, or deposit on UK Data Service / Figshare with an accompanying methods paper.

Content: the dataset itself, documentation of the methodology, validation against published aggregates, discussion of limitations (cross-boundary registration, practice closures, COVID payment protection effects).

## Reference implementations

- House of Commons Library: https://github.com/houseofcommonslibrary/local-health-data-from-QOF
  (R, single year 2019/20, includes LSOA-level apportionment with census weighting)
- NHS Digital QOF GitHub: https://github.com/NHSDigital/QOF
  (code used to produce the 2022/23 publication)

## Integration with wellbeing project

The output CSV (`data/qof_hypertension_la.csv`) plugs directly into the wellbeing project:

```bash
python qof_panel.py
```

`qof_panel.py` auto-detects `qof_hypertension_la.csv` (LA-level, from this pipeline) in preference to `qof_hypertension_utla.csv` (UTLA-level, from Fingertips). This gives ~285 English LAs instead of ~127, preserving the district-level granularity that makes the area classification analysis rich.
