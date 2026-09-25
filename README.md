# UK Well-being and Social Care Workforce Panel

## Overview

This repository contains Python code to build three longitudinal research panels:

1. **UK Well-being Trajectories Panel** — ONS Annual Personal Well-being
   estimates at local authority level, 2011-2023, for 354 UK local authorities.

2. **England Social Care Workforce Panel** — Retail store counts, social care
   vacancies and workforce metrics, claimant count, population, and overseas
   worker share for 153 English upper-tier local authorities, 2016-2023.

3. **Scotland Social Care Panel** (built July 2026) — Retail store counts,
   SSSC/Care Inspectorate vacancy rate, claimant count, and population for
   32 Scottish council areas, 2016-2023 (vacancy rate 2020-2023 only). See
   `README.SCOT` for full build history and methodology decisions.

Both panels are built from openly available administrative and survey data
using a reproducible Python pipeline. See README_FIRST.md for a plain-language
overview and QUICK_START.md for step-by-step setup instructions.

---

## Panel Data Files

After building, the following analysis-ready CSV files are produced:

### england_panel_base.csv
`data/intermediate/england_panel_base.csv`

Base England panel at **lower-tier local authority level** (296 English LADs).
One row per LA × year × well-being measure (long format).

| Column | Description |
|--------|-------------|
| la_code | ONS LAD23 code (E06/E07/E08/E09) |
| la_name | Local authority name |
| year | Calendar year (2016-2023) |
| nation | = 'England' |
| region | Government Office Region |
| claimants_mean | Annual mean Experimental Claimant Count (JSA + UC) |
| pop_total | Total population (ONS Mid-Year Estimates) |
| pop_65plus | Population aged 65+ (derived from MYE) |
| overseas_share | Share of health & social work employment held by non-UK nationals (HMRC PAYE) |
| measure | Well-being measure (life-satisfaction, worthwhile, happiness, anxiety) |
| value | Mean well-being score (0-10 scale) |
| se | Standard error (derived from ONS 95% CI) |
| ci_lower | Lower 95% confidence interval |
| ci_upper | Upper 95% confidence interval |

**Well-being data:** Available 2016-2022 (ONS paused LA-level publication
October 2024 due to APS response rate issues). 2023 rows present with NaN
well-being values.

### england_panel_sfc.csv
`data/intermediate/england_panel_sfc.csv`

Full England panel at **upper-tier local authority level** (153 LAs) for
Bartik IV analysis. One row per LA × year × well-being measure (long format).

| Column | Description |
|--------|-------------|
| la_code | Upper-tier code (E06/E08/E09 unitaries, E10 counties, or combined codes) |
| la_name | Local authority name |
| year | Calendar year (2016-2023) |
| nation | = 'England' |
| region | Government Office Region |
| measure | Well-being measure |
| value | Well-being score (approximate — see geography note below) |
| tot | Total major retailers (Geolytix, aggregated to upper-tier) |
| tot_new | Discounters: Aldi + Lidl |
| tot_old | Incumbents: Tesco, Asda, Sainsburys, Morrisons, Iceland, M&S, Waitrose |
| claimants_mean | Annual mean claimant count (aggregated to upper-tier) |
| pop_total | Total population (aggregated to upper-tier) |
| pop_65plus | Population aged 65+ (aggregated to upper-tier) |
| overseas_share | Regional overseas worker share (HMRC PAYE, SIC 86-88) |
| filled_posts | Filled posts, independent sector (Skills for Care ASCWDS) |
| employees | Employees, independent sector |
| vacant_posts | Vacant posts (suppressed for small LAs — see note) |
| vacancy_rate | Vacancy rate = vacant / (filled + vacant) |
| fte_posts | Full-time equivalent filled posts |

### retail_data_england.csv / retail_data_scotland.csv
`data/intermediate/retail_data_england.csv`
`data/intermediate/retail_data_scotland.csv`

Retail store counts at lower-tier LAD level, 2016-2023. Used as input to
the panel assembly. England: 295 LADs × 8 years. Scotland: 32 council areas × 8 years.

---

## Geography Notes

### Upper-tier vs lower-tier local authorities

England has two tiers of local government in non-metropolitan areas:

- **Upper-tier (county councils, E10):** responsible for social care
- **Lower-tier (district councils, E07):** responsible for housing, planning

Skills for Care publishes workforce data at upper-tier level (counties +
unitaries = ~151 areas). The retail data from Geolytix is at store level
and can be aggregated to either tier.

This pipeline aggregates all lower-tier data (retail, claimants, population)
to upper-tier using the ONS LAD23_CTY23 lookup, producing a consistent
153-LA panel that matches the Skills for Care geography.

**Consequence for retail counts:** National totals are identical whether
measured at lower or upper tier (verified: see check_retail_totals.py).
However, the median per LA is higher at upper-tier because the same
national stock of stores is spread across fewer, larger units. This is
expected and documented in RETAIL_METHODOLOGY_NOTE.md.

### Well-being at upper-tier geography

The ONS publishes well-being estimates at lower-tier LA level. When we
aggregate districts to counties, we average district-level estimates.
This is methodologically imperfect because:

1. ONS does not publish county-level well-being — it is not a recognised
   unit of analysis for this data
2. Averaging imprecise district-level estimates introduces additional
   uncertainty not captured by the standard errors
3. Some districts within a county may have very different well-being levels

**The well-being columns in england_panel_sfc.csv should be treated as
indicative context only.** For well-being analysis, use england_panel_base.csv
(lower-tier, proper geography) or the dedicated well-being pipeline outputs.

For the Bartik IV analysis, the outcome variables are Skills for Care
metrics (vacancies, filled posts, vacancy rate) — not well-being.

### Vacancy rate suppression

Skills for Care suppresses vacancy rate data for small local authorities
to protect confidentiality. Approximately 25% of LA-year observations
have suppressed vacancy rates (set to NaN). Filled posts and employees
are not suppressed. The mean vacancy rate reported in cohort tables
is based on available (non-suppressed) observations.

### Overseas worker share

The overseas_share variable is from HMRC PAYE data for health and social
work (SIC 86-88 combined). This is broader than the Skills for Care
independent sector (SIC 87+88 only) because SIC 86 includes NHS workers.
Overseas share is slightly understated for the independent care sector
specifically. This matches the definition used in Radakrishnan et al.
(2025), which used ONS Annual Population Survey data for the same
SIC 86-88 sector. PAYE data has no sampling error but records nationality
at NI registration, so naturalised citizens appear as UK nationals.

---

## Data Sources

| Source | Variable | Geography | Period | Access |
|--------|----------|-----------|--------|--------|
| Geolytix Retail Points | Retail store counts | Store (postcode/coordinates) | 2014-2025 | Commercial licence |
| Skills for Care ASCWDS | Vacancies, employees, FTE | Upper-tier LA | 2016-2024 | Free download |
| ONS Experimental Claimant Count (Nomis NM_162_1) | Claimant count | LA (TYPE464) | 2016-present | Free API |
| ONS Mid-Year Estimates (Nomis) | Population, age structure | LA | 2016-2023 | Free download |
| HMRC PAYE nationality by region and industry | Overseas worker share | GOR region | 2014-2024 | Free download |
| ONS Annual Personal Well-being | Well-being scores | Lower-tier LA | 2011-2023 | Free download |
| ONS 2011 Area Classification | Area typology | LA | 2011 (static) | Free download |
| ONS LAD23_CTY23 | District-to-county lookup | LA | 2023 | Free API |

### Download URLs

**ONS Well-being:**
https://download.ons.gov.uk/downloads/datasets/wellbeing-local-authority/editions/time-series/versions/4.csv

**ONS Area Classification:**
https://www.ons.gov.uk/file?uri=/methodology/geography/geographicalproducts/areaclassifications/2011areaclassifications/datasets/clustermembershipv2.xls

**Skills for Care trended data:**
https://www.skillsforcare.org.uk/Adult-Social-Care-Workforce-Data/workforceintelligence/resources/Local-authority-areas.aspx

**HMRC PAYE regional data:**
https://www.gov.uk/government/statistics/payrolled-employments-in-the-uk-by-nationality-region-and-industry

**ONS Population Estimates (Nomis):**
https://www.nomisweb.co.uk/datasets/pestsyoala

**Geolytix Retail Points:**
https://geolytix.com/geodata/ (commercial licence required)

---

## Boundary Harmonisation

The well-being series spans 12 years during which 12 LA boundary changes
occurred. These are handled differently depending on type:

### True mergers (aggregated UP)

Multiple districts merged into a single new unitary authority. Predecessor
data is aggregated using population-weighted means.

| Year | New authority | Predecessors |
|------|--------------|--------------|
| 2019 | East Suffolk | Suffolk Coastal, Waveney |
| 2019 | West Suffolk | Forest Heath, St Edmundsbury |
| 2019 | Somerset West & Taunton | Taunton Deane, West Somerset |
| 2020 | Buckinghamshire | Aylesbury Vale, Chiltern, South Bucks, Wycombe |
| 2023 | North Yorkshire | 7 predecessor districts |
| 2023 | Somerset | 4 predecessor districts |

### County splits (combined BACK)

Three counties were abolished and replaced by multiple unitaries. ONS
publishes the new codes with only partial backfilled data (1-4 years).
We combine the split parts back to their original county footprint:

| Original | Split into | Combined code |
|----------|-----------|---------------|
| Dorset | BCP + Dorset UA (2019) | DORSET_COMBINED |
| Northamptonshire | North + West (2021) | NORTHANTS_COMBINED |
| Cumbria | Cumberland + Westmorland & Furness (2023) | CUMBRIA_COMBINED |

### Scottish code remapping

Four Scottish council area codes changed after boundary revisions. Old
codes in ONS data are remapped to current LAD23 codes.

### Claimant count harmonisation

The Nomis claimant count API returns data using codes active at collection
time. Pre-merger data uses predecessor codes. The same boundary
harmonisation applied to well-being data is applied to claimant count
after download to ensure consistent codes across all panel files.

---

## Pipeline Architecture

```
Geolytix v1-v36  ──→ retail_panel.py ──→ retail_data_england.csv
                                     └──→ retail_data_scotland.csv

Nomis API ────────→ panel_data.py ───→ claimant_count_annual.csv
                                  └──→ population_annual.csv

HMRC PAYE ────────→ paye_overseas.py → paye_overseas_regional.csv
                                   └──→ paye_overseas_la.csv

Skills for Care ──→ skills_for_care.py → skillsforcare_england.csv

ONS Well-being ───→ (existing pipeline) → wellbeing_harmonised_panel.csv
                    data_loading.py
                    boundaries.py

                    ┌─────────────────────────────────────┐
All of the above ──→│      assemble_england.py            │──→ england_panel_base.csv
                    │  (lower-tier, 296 LAs, with WB)    │
                    └─────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────────┐
                    │    assemble_england_sfc.py          │──→ england_panel_sfc.csv
                    │  (upper-tier, 153 LAs, with SfC)   │
                    └─────────────────────────────────────┘
                              │
                              ▼
                    cohort_report.py ──→ output/cohort/
                                        table1_by_year.html
                                        table1_by_region.html
                                        fig_trends.png
                                        fig_retail_by_region.png
                                        fig_overseas_by_region.png
                                        fig_claimants_by_region.png
                                        fig_vacancies_by_region.png
```

---

## Bartik Instrument Construction Notes

The Bartik instrumental variable in Radakrishnan et al. (2025) is:

```
Bartik_it = Σ_k (share_k,i,2016 × growth_k,t,national)
```

Where:
- k indexes chain type (discount = Aldi/Lidl, incumbent = rest)
- i indexes local authority
- 2016 is the baseline year (predetermined composition)
- growth is national chain-specific growth excluding LA i (leave-one-out)

**To construct from our panel:**

1. Filter `england_panel_sfc.csv` to year == 2016
2. Calculate: `discount_share_2016 = tot_new / tot`
3. Calculate national growth rates from total counts (leave-one-out):
   `growth_discount_t = (sum(tot_new, all LAs except i, year t) /
                         sum(tot_new, all LAs except i, year 2016)) - 1`
4. Bartik = discount_share_2016 × growth_discount + (1 - discount_share_2016) × growth_incumbent

**See RETAIL_METHODOLOGY_NOTE.md** for explanation of why our retail
counts differ from the original paper (same national total, different
median due to upper-tier aggregation).

### Regional-level analysis (Section 4, `bartik_check.py`)

Beyond the main 148/153-LA analysis (Section 3), `bartik_check.py`
also runs a regional-level check (9 English regions) testing whether
overseas worker recruitment moderates the retail effect. Current
design (settled after substantial iteration — see chat history if
questions arise):

- **Stage 1 (single, shared across all regions):** `tot ~ bartik_region
  + constant`, where `bartik_region` is the region-year mean of the
  already-computed LA-level `bartik` instrument (not a fresh
  region-level reconstruction — that was tried and produced a
  materially different, undesired quantity).
- **Stage 2:** `outcome ~ tot_hat + year FE + overseas_share
  (contemporaneous, year-by-year) + region fixed effects`.
- Overseas_share is **contemporaneous**, not a fixed baseline year —
  deliberate choice, since 2016 predates the entire relevant visa
  policy history (Health & Care Worker route launched Aug 2020; social
  care added to Shortage Occupation List Feb 2022). Known tradeoff:
  contemporaneous overseas_share may be partly a mediator if overseas
  recruitment responds within-year to retail-driven staff loss —
  accepted rather than resolved, in the interest of not conflating the
  moderator with a policy-invalid predetermined snapshot.
- Multiple earlier designs (binary high/low split, continuous
  interaction with a from-scratch region-level Bartik) were tried and
  abandoned — each either collapsed the first-stage identification
  (N=9 regions cannot support more than one coefficient's worth of
  identifying variation) or mixed incompatible instrument
  constructions. **Do not revert to these** without a clear reason.
- Results: all four outcomes (vacant posts, vacancy rate, benefit rate
  Dec, benefit rate annual) null, first-stage F=12.53. Treat as a
  scoping exercise (9 clusters, stage 2 has more parameters than
  clusters) — not a reliable causal estimate on its own.

---

## Well-being Pipeline (Separate)

The well-being trajectory analysis is a separate, earlier pipeline.
Key scripts:

| Script | Purpose |
|--------|---------|
| main.py | Trajectory analysis (OLS/WLS slopes, classification) |
| maps.py | Choropleth maps of trajectories |
| analysis.py | Trend fitting, Kruskal-Wallis tests, plots |
| boundaries.py | Boundary harmonisation (mergers + splits) |
| data_loading.py | Load ONS well-being CSV and area classification XLS |
| export_curated.py | Export harmonised panel for distribution |

Key outputs: `data/curated/wellbeing_harmonised_panel.csv` (354 LAs × 12
years × 4 measures, with standard errors).

Key finding: Pre-COVID (2011-2019) shows broad-based improvement across
all area types. Full-period estimates (2011-2023) conflate secular trends
with COVID disruption and differential recovery. Pre-COVID estimates are
required for parallel trends validation in difference-in-differences
designs.

---

## Consistency Checks

After building the panels, run:

```bash
python check_panel.py              # Panel completeness and balance
python check_paper_consistency.py  # Compare to paper Table 2
python check_retail_totals.py      # Verify national retail totals
```

Expected results vs Radakrishnan et al. (2025) Table 2:
- Retail medians ~20% higher (fewer, larger upper-tier units — same national total)
- Vacancy levels slightly higher (153 vs 150 LAs, suppression affects mean)
- Claimant counts ~8-10% higher (larger upper-tier geographic units)
- Year-on-year trends identical in direction

---

## TODO: Extensions

**Extend panel to 2024/25:**
Download updated Skills for Care trended data file (released October each year).
Replace `data/skillsforcare/Trendeddatadownload201617to202324.xlsx`.
Update `YEAR_MAX = 2024` in `panel_data.py` and `retail_panel.py`.

**Scotland social care panel:** STATUS (July 2026) — BUILT. `scotland_panel.py`
assembles retail + claimants + population + SSSC vacancy_rate for all 32
council areas, 2016-2023 (vacancy_rate 2020-2023 only — SSSC source
constraint). Bartik instrument validated on a 29-council specification
(3 remote island authorities excluded on structural grounds — see
`README.SCOT` Section 3). Main IV results obtained: social care vacancy
null replicates England's; benefit-claims effect does NOT replicate
(genuine divergence, not underpowered — see `README.SCOT` Section 6).
Full build history, data source decisions, and open items in `README.SCOT`.

**ONS well-being resumption:**
ONS paused LA-level well-being publication October 2024 (APS response
rate concerns). Monitor:
https://www.ons.gov.uk/peoplepopulationandcommunity/wellbeing
When resumed, re-run `python make.py curated` and `python make.py england-panel`
to incorporate new data.

---

## Methodological Reflection: Identification vs. Data Granularity

**Intended for the paper's discussion/limitations section** — recorded
here so it isn't lost between chats.

Section 3's instrument is strong (F=30.84, well above Stock-Yogo) —
real internal validity for the main effect. But testing whether that
effect is *moderated* by overseas recruitment access — a natural,
policy-relevant follow-up — runs into a constraint no amount of
instrument strength can resolve: the only overseas-worker data that
exists (HMRC PAYE by industry) is published at just 9 English regions,
not at LA level. Every regional-level specification tried (Section 4,
above, and several abandoned variants) returns an honest null or an
unidentifiable estimate — not because the design is wrong, but because
9 regions cannot support the precision the underlying policy question
needs.

**General point:** a valid instrument establishes that a given LATE is
credible — it does not establish that any question one might ask of
that treatment is answerable with the same data. Mechanism and
heterogeneity questions routinely need finer resolution than the
headline effect, and where that resolution doesn't exist in the
available administrative data, no amount of identification-strategy
quality can substitute for it. Worth stating plainly rather than
apologising for: this is a structural feature of the data, not a flaw
in the analysis, and arguably a quiet contributor to why policy debates
about mechanism often can't be settled by the data being cited in them.

A second PhD project (using RAPID data) is planned to pursue the
granular version of this question that the current data cannot answer.
See `README.SCOT` Section 9 for full context.

---

If you use this code or data, please cite:

Radhakrishnan, R. & McMeekin, P. (2026). (2026).
[A Harmonised Longitudinal Panel of Local Authority Well-being in the United Kingdom, 2011-2023: Dataset Construction and Trajectory Analysis].

And the underlying data sources as listed in the Data Sources section.

---

## Licence

- Code: MIT Licence
- ONS data: Open Government Licence v3.0
- HMRC PAYE data: Open Government Licence v3.0
- Skills for Care data: Open Government Licence v3.0
- Geolytix data: Commercial licence (not redistributable)
- Curated panel datasets: CC-BY 4.0

## Contact

Peter McMeekin — peter.mcmeekin@northumbria.ac.uk  
Northumbria University, Department of Nursing, Midwifery and Health
