# Quick Start Guide

## Before You Begin

You need:
- Python 3.8 or later
- Internet connection (for automatic data downloads)
- The Geolytix Retail Points files (v1-v36) — these require a Geolytix
  licence and must be obtained separately
- The Skills for Care trended data Excel file — free download (see below)

---

## Step 1: Set Up Python Environment

Open a terminal (PowerShell on Windows, Terminal on Mac/Linux) and run:

```bash
cd C:\path\to\this\project

# Create virtual environment (one-time setup)
python -m venv wellbeing_env

# Activate it (do this every time you work on the project)
wellbeing_env\Scripts\activate        # Windows
source wellbeing_env/bin/activate     # Mac/Linux

# Install required packages (one-time setup)
pip install -r requirements.txt
```

You'll see `(wellbeing_env)` at the start of your prompt when the
environment is active.

---

## Step 2: Set Up Data Directories

```bash
mkdir data\geolytix
mkdir data\skillsforcare
mkdir data\nomis
mkdir data\paye
mkdir data\intermediate
```

---

## Step 3: Add Data Files That Cannot Be Auto-Downloaded

**Geolytix Retail Points (requires licence):**
Copy your Geolytix snapshot files (v1-v36) into `data\geolytix\`.
Files must be named: `geolytix_retailpoints_vN_YYYYMM.csv`

**Skills for Care trended data (free download):**
Download from:
https://www.skillsforcare.org.uk/Adult-Social-Care-Workforce-Data/workforceintelligence/resources/Local-authority-areas.aspx
Save as: `data\skillsforcare\Trendeddatadownload201617to202324.xlsx`

**ONS Population estimates (free download):**
Download from: https://www.nomisweb.co.uk/datasets/pestsyoala
Select: local authorities district/unitary (April 2023), all areas,
years 2016-2023, Gender=Total, Age=All ages + 0-15 + 16-64
Save as: `data\nomis\NOMIS_POP.csv`

**Well-being data (free download):**
Download from:
https://download.ons.gov.uk/downloads/datasets/wellbeing-local-authority/editions/time-series/versions/4.csv
Save as: `data\wellbeing_la.csv`

**ONS Area Classification (free download):**
Download from:
https://www.ons.gov.uk/file?uri=/methodology/geography/geographicalproducts/areaclassifications/2011areaclassifications/datasets/clustermembershipv2.xls
Save as: `data\cluster_membership.xls`

---

## Step 4: Check Everything Is In Place

```bash
python check_geolytix.py
```

This will confirm Geolytix files are found and correctly formatted.

---

## Step 5: Build the Panels

Run targets in this order:

```bash
# 1. Retail store counts (England + Scotland)
python make.py retail

# 2. Claimant count + population (downloads from Nomis API)
python make.py panel-data

# 3. HMRC PAYE overseas worker share (downloads automatically)
python make.py paye

# 4. Skills for Care workforce data
python make.py skillsforcare

# 5. Base England panel (joins 1-3 + well-being)
python make.py england-panel

# 6. Full England panel with Skills for Care (upper-tier geography)
python make.py england-sfc

# 7. Cohort report (Table 1 + charts)
python make.py cohort-report
```

Or run everything at once (after completing Steps 3-4):

```bash
python make.py retail
python make.py panel-data
python make.py paye
python make.py skillsforcare
python make.py england-panel
python make.py england-sfc
python make.py cohort-report
```

---

## Step 6: Check Outputs

```bash
python check_panel.py        # Verifies all intermediate files
python check_paper_consistency.py  # Compares to Radakrishnan et al. Table 2
```

Output files are in:
- `data/intermediate/` — panel CSV files for econometric analysis
- `output/cohort/` — Table 1 HTML files and PNG charts

---

## Running Offline (Pre-downloading All Data)

Some data is downloaded automatically from APIs (claimant count from
Nomis, population estimates, PAYE data, LAD boundaries). To run
completely offline, pre-download these before disconnecting:

```bash
# Download and cache all API data
python make.py panel-data    # Downloads claimants + population
python make.py paye          # Downloads PAYE overseas data
python make.py retail        # Downloads LAD boundaries (for spatial join)
```

Once cached, all subsequent runs use local files only. Cached files are in:
- `data/intermediate/claimant_count_annual.csv`
- `data/intermediate/population_annual.csv`
- `data/intermediate/paye_overseas_regional.csv`
- `data/intermediate/paye_overseas_la.csv`
- `data/la_boundaries_lad23.geojson`
- `data/lad_to_county.csv`

To force a re-download of any file, delete it and re-run the relevant target.

---

## Well-being Trajectory Analysis (Separate Pipeline)

The well-being analysis is a separate pipeline from the social care
panel. To run it:

```bash
python make.py all           # Full well-being analysis (all levels)
python make.py supergroup    # Supergroup level only
python make.py maps          # Maps only
```

Outputs go to `output/supergroup/`, `output/group/`, `output/subgroup/`.

---

## All Make Targets

| Target | What it does |
|--------|-------------|
| `retail` | Retail counts from Geolytix (England + Scotland) |
| `panel-data` | Claimants + population from Nomis |
| `paye` | HMRC PAYE overseas worker share |
| `skillsforcare` | Skills for Care ASCWDS data |
| `england-panel` | Base England panel (lower-tier, with well-being) |
| `england-sfc` | Full England panel (upper-tier, with Skills for Care) |
| `cohort-report` | Table 1 + charts |
| `supergroup` | Well-being trajectories at supergroup level |
| `group` | Well-being trajectories at group level |
| `subgroup` | Well-being trajectories at subgroup level |
| `maps` | Choropleth maps |
| `curated` | Export curated well-being datasets |
| `robustness` | Well-being robustness checks |
| `all` | Full well-being pipeline (all levels) |
| `clean` | Delete all outputs |
| `status` | Show what outputs exist |

---

## If Something Goes Wrong

**"Module not found"** — virtual environment not activated. Run:
`wellbeing_env\Scripts\activate`

**"File not found: data\geolytix\..."** — Geolytix files not in the
right directory. Check filenames match pattern `geolytix_retailpoints_vN_YYYYMM.csv`

**"ERROR: Missing input files"** — run the prerequisite targets first.
Each target tells you what it needs.

**API download fails** — check internet connection. Nomis and ONS APIs
are occasionally slow. Re-running usually works.

**Results differ from paper** — see RETAIL_METHODOLOGY_NOTE.md for
explanation of expected differences in retail counts.
