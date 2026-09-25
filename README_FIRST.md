# README FIRST

## What This Project Does

This project builds longitudinal data panels for two related research programmes
at Northumbria University, both supported by the NIHR IDEAS programme.

**Programme 1 — UK Well-being Trajectories (lead: Peter McMeekin)**

Tracks how subjective well-being (life satisfaction, happiness, anxiety,
worthwhile) has changed across 354 UK local authorities from 2011 to 2023,
using ONS Annual Population Survey data. The analysis asks: which types of
places improved, which deteriorated, and which stayed stable?

Output: trajectory classifications, maps, and a harmonised longitudinal
panel suitable for policy evaluation.

**Programme 2 — Retail Competition and Social Care Workforce (lead: Ramakrishnan Radhakrishnan)**

Tests whether the expansion of discount supermarkets (Aldi and Lidl) into
English local areas causes shortages in the adult social care workforce,
using a Bartik instrumental variable design. The short answer from the
published paper: it doesn't, because international recruitment buffers
the effect.

This codebase extends that work by building a replicable Python pipeline
for the data that underpins the analysis.

---

## Who Should Read What

**I am an economist who wants to run the models:**
→ Read QUICK_START.md, then README.md section "Panel data files"

**I am a researcher who wants to use the well-being data:**
→ Read QUICK_START.md, then README.md section "Well-being panel"

**I am a software engineer trying to understand the pipeline:**
→ Read README.md in full

**I am a reviewer or collaborator checking the methodology:**
→ Read README.md sections "Data sources", "Boundary harmonisation",
  "Geography note on upper-tier aggregation", and RETAIL_METHODOLOGY_NOTE.md

---

## What This Is Not

This project does **not** run the econometric models (fixed effects, Bartik IV,
two-stage least squares). That analysis is in Ramakrishnan's Stata code.

This project builds the **analysis-ready datasets** that feed into those models:
clean, harmonised, documented panel CSVs that can be loaded directly into
Stata, R, or Python for estimation.

---

## Key Concepts for Non-Coders

**What is a panel dataset?**
A dataset where the same units (here: local authorities) are observed
repeatedly over time (here: annually, 2016-2023). This allows researchers
to control for stable differences between places and focus on what changes
within each place over time.

**What is a make file / build system?**
A set of instructions that builds the dataset step by step. Like a recipe
— each step depends on the previous one. Running `python make.py all`
follows the recipe from start to finish. You don't need to understand
each step to run it.

**What is a Bartik instrument?**
A statistical technique for establishing causation rather than just
correlation. The idea: Aldi and Lidl expanded nationally for reasons
unrelated to any individual local area (corporate strategy, COVID consumer
behaviour). Areas that happened to have more Aldi/Lidl stores in 2016
experienced more predicted retail expansion after 2020. This
"predetermined exposure" is used to isolate the causal effect of retail
expansion on care sector outcomes.

**What is boundary harmonisation?**
Local authority boundaries changed 12 times between 2011 and 2023.
Some councils merged, some counties were split into new unitaries.
This makes longitudinal analysis difficult — you can't directly compare
a 2012 figure for "Northamptonshire" with a 2022 figure for "North
Northamptonshire" because they're different geographic units.
This codebase handles these changes automatically.

---

## Structure at a Glance

```
wellbeing_project/
  make.py              ← Run this to build everything
  README_FIRST.md      ← You are here
  QUICK_START.md       ← Start here to get running
  README.md            ← Full technical documentation

  Core pipeline:
  retail_panel.py      ← Retail store counts from Geolytix
  panel_data.py        ← Claimants + population from Nomis
  paye_overseas.py     ← Overseas worker share from HMRC PAYE
  skills_for_care.py   ← Social care workforce from Skills for Care
  assemble_england.py  ← Joins everything into base England panel
  assemble_england_sfc.py ← Adds Skills for Care at upper-tier geography

  Well-being pipeline (separate):
  main.py              ← Well-being trajectory analysis
  maps.py              ← Choropleth maps
  analysis.py          ← Trend fitting and classification

  Data inputs (you provide or download):
  data/
    geolytix/          ← Geolytix retail point snapshots (v1-v36)
    skillsforcare/     ← Skills for Care trended data Excel file
    nomis/             ← Population estimates from Nomis
    paye/              ← HMRC PAYE regional data
    curated/           ← Processed well-being panel (auto-generated)

  Data outputs (auto-generated):
  data/intermediate/   ← Intermediate panel CSVs
  output/              ← Charts, tables, maps
```

---

## Data Availability

All source data used in this project is either:
- **Open government data** published by ONS, HMRC, Skills for Care,
  or NHS Digital under the Open Government Licence
- **Commercially licensed** (Geolytix Retail Points — requires licence)

The processed panel datasets can be shared subject to the underlying
data licences. See README.md for full data source details and download
links.

---

## Contact

Peter McMeekin  
Department of Nursing, Midwifery and Health  
Northumbria University  
peter.mcmeekin@northumbria.ac.uk
