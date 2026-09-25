# QOF Practice-Level Data: Download Guide

## Overview

To build LA-level QOF prevalence from practice-level data, you need:
1. **QOF prevalence by practice** — one file per year (cardiovascular group contains hypertension)
2. **GP practice to LA lookup** — maps each practice to its lower-tier local authority

## 1. QOF Practice-Level Prevalence Files

All files are from the NHS Digital QOF publication series. Navigate to the
publication page for each year and download the **cardiovascular group**
practice-level file (contains hypertension register counts and list sizes).

Save all files into: `data/qof_practice/`

### Publication pages (navigate and download the cardiovascular practice-level CSV/XLSX):

| Year | Publication URL |
|------|---------------|
| 2012-13 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2012-13 |
| 2013-14 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2013-14 |
| 2014-15 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2014-15 |
| 2015-16 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2015-16 |
| 2016-17 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2016-17 |
| 2017-18 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2017-18 |
| 2018-19 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/quality-and-outcomes-framework-qof-2018-19 |
| 2019-20 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2019-20 |
| 2020-21 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2020-21 |
| 2021-22 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2021-22 |
| 2022-23 | https://digital.nhs.uk/data-and-information/publications/statistical/quality-and-outcomes-framework-achievement-prevalence-and-exceptions-data/2022-23 |

### What to download from each page:

Look for the file named something like:
- "Prevalence, achievement and exceptions, cardiovascular group, GP practice level"
- Or: "QOF YYYY-YY: Prevalence... cardiovascular group... practice level"

The file will be CSV or XLSX. It contains one row per practice per indicator,
with columns for practice code, register count, list size, and prevalence %.

The hypertension indicator code is **HYP001** (register) across all years.

### File naming convention:

Save each file as: `data/qof_practice/qof_cardio_YYYY.csv` (or .xlsx)

For example:
- `data/qof_practice/qof_cardio_2012.csv`
- `data/qof_practice/qof_cardio_2013.csv`
- etc.

The processing script will detect CSV or XLSX automatically.


## 2. GP Practice to LA Lookup

### Option A: ODS Data Search and Export + NSPL (recommended)

The Organisation Data Service (ODS) publishes the GP practice registry
(epraccur) with postcodes. The ONS National Statistics Postcode Lookup
(NSPL) maps postcodes to lower-tier LAs.

1. **epraccur** (GP practice file):
   The old CSV downloads were retired in September 2025 and replaced by the
   Data Search and Export (DSE) tool. The epraccur predefined report should
   auto-download from:
   https://digital.nhs.uk/services/organisation-data-service/data-search-and-export/csv-downloads/gp-and-gp-practice-related-data
   
   If that doesn't work, go to DSE directly:
   https://www.odsdatasearchandexport.nhs.uk/
   Find the "epraccur" predefined report and download as CSV.
   
   Save as: `data/epraccur.csv`
   
   Note: DSE reports are dynamic (updated nightly) and include all records
   open or closed since 31 March 2017. Filter to active practices in the
   processing script.

2. **NSPL** (National Statistics Postcode Lookup):
   Download from data.gov.uk:
   https://www.data.gov.uk/dataset/7ec10db7-c8f4-4a40-8d82-8921935b4865/national-statistics-postcode-lookup-uk
   
   Or from the Open Geography Portal:
   https://geoportal.statistics.gov.uk (search "NSPL")
   
   This downloads as a ~178MB zip. Extract it and find the main CSV file
   in the Data folder (e.g. NSPL_AUG_2025_UK.csv).
   Save as: `data/nspl.csv`
   
   You only need columns: pcds (postcode) and laua (LA code).

### Option B: Use the QOF mapping file (simpler but coarser)

From 2015-16 onwards, each QOF publication includes a mapping file that shows
each practice's CCG/Sub-ICB. This doesn't give you lower-tier LA directly,
but combined with a CCG-to-LA lookup it gets you close (though with the
boundary mismatch issues we discussed).

### Option C: House of Commons Library approach

The houseofcommonslibrary/local-health-data-from-QOF GitHub repo contains
R code and lookup tables for practice-to-LSOA-to-LA mapping for 2019/20.
Their `inputs/lsoa_geog_lookup.csv` contains LSOA to LA mappings.
Their approach is more sophisticated (age-adjusted, census-weighted) but
only covers one year. Their lookups could be adapted for other years.
https://github.com/houseofcommonslibrary/local-health-data-from-QOF


## 3. Summary of files needed

```
data/
  qof_practice/
    qof_cardio_2012.csv (or .xlsx)
    qof_cardio_2013.csv
    qof_cardio_2014.csv
    qof_cardio_2015.csv
    qof_cardio_2016.csv
    qof_cardio_2017.csv
    qof_cardio_2018.csv
    qof_cardio_2019.csv
    qof_cardio_2020.csv
    qof_cardio_2021.csv
    qof_cardio_2022.csv
  epraccur.csv          (GP practice registry with postcodes)
  nspl.csv              (or onspd.csv — postcode to LA lookup)
```

## 4. Notes

- The QOF file format changed over the years. Pre-2015 files tend to be
  XLSX with multiple sheets. 2015+ files are more likely to be CSVs.
  The processing script handles both.
  
- The epraccur file from DSE contains ALL practices including closed ones.
  The processing script filters to active practices. DSE reports are dynamic
  and update nightly — the data reflects the current state, not a snapshot.
  For historical practice lists, you may need the TRUD ODS weekly packs.

- Some practices serve patients across LA boundaries. The postcode-based
  lookup assigns each practice to the LA of its *premises*, not its
  patients. This is standard practice in the literature and works well
  at LA level (most patients live near their GP).

- The NSPL/ONSPD is updated quarterly. Use the version closest to the
  middle of your study period, or download multiple versions if you want
  to track postcode-to-LA changes over time (rare at LA level).
