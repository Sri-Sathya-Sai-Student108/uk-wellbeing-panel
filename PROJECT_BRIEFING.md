# Wellbeing Trajectories Project — Claude Project Briefing

## Overview

This is a research project analysing longitudinal well-being trajectories across UK local authorities (2011-2023), led by Peter at Northumbria University to support an early career researcher (ECR) who is a data scientist learning panel methods. The project has a working codebase and preliminary results. This document provides context for continuing development in a new Claude Project.

## What exists

### Codebase (Python, in a directory called wellbeing_project/)

| File | Purpose |
|------|---------|
| config.py | Supergroup/group/subgroup names, measure labels |
| boundaries.py | 6 LA true mergers + 3 county splits (2019-2023), BOUNDARY_MERGES dict for true mergers, BOUNDARY_SPLITS dict for county splits, SPLIT_CLASSIFICATIONS dict with manual assignments and rationale, population weights, harmonise_boundaries() aggregates predecessors UP to new codes, combine_splits() aggregates split parts BACK to county footprint (default), propagate_classification() handles both cases, Scottish code remapping, Lincolnshire code handling, Cornwall/Scilly fix |
| data_loading.py | Load wellbeing CSV and classification XLS, extract standard errors from confidence intervals (se = CI width / 3.92), handles ONS formatting quirks |
| analysis.py | OLS/WLS trend fitting with inverse-variance weighting (default), trajectory classification, Kruskal-Wallis tests, plots. Weighted least squares: w = 1/se², β = (X'WX)^-1 X'Wy. Falls back to OLS if SEs invalid. |
| main.py | Trajectory analysis with --level, --england-only, --no-combine-splits, --no-weighting flags. Default: weighted, combined splits. Outputs report showing estimation method used. |
| maps.py | Choropleth maps using LAD23 boundaries from ONS ArcGIS API, combine_boundary_splits() dissolves split geometries, handles combined splits by default, --no-combine-splits flag available |
| make.py | Build script (clean, all, status, per-level targets, curated export) |
| qof_panel.py | Fixed effects panel model (wellbeing ~ QOF prevalence), England-only, always combines splits for balanced panel analysis |
| export_curated.py | Exports analysis-ready CSVs including SEs for data release |
| requirements.txt | pandas numpy matplotlib scipy openpyxl xlrd geopandas fingertips_py linearmodels |
| qof_setup/ | QOF practice-level download helper and processing pipeline (not yet tested end-to-end) |
| papers/cohort_description/paper.tex | Draft data descriptor + methods paper with national comparison |
| papers/cohort_description/build.bat | Paper build script |

### Data files (in data/ subdirectory, not in repo)

- wellbeing_la.csv — ONS Annual Personal Well-being, local authority level, v4
- cluster_membership.xls — ONS 2011 Area Classification for LAs
- la_boundaries_lad23.geojson — cached LAD23 boundaries from ONS API
- qof_hypertension_utla.csv — Fingertips UTLA-level (127 LAs only, needs replacing with practice-level)

### Output structure

```
output/
  supergroup/
    tables/    (report.txt showing WLS/OLS method, wellbeing_trajectories.xlsx)
    plots/     (trajectories_*.png, slopes_*.png, heatmap_*.png, four_measures_panel.png)
    maps/      (map_classification_*.png, map_trajectory_*.png, map_baseline_*.png, map_slope_*.png)
  group/, subgroup/, supergroup_england/ (same structure)
  qof_panel/ (fe_model_results.txt, panel_data.csv, scatter plots)
  curated/ (wellbeing_harmonised_panel.csv with SEs, area_classification_354.csv, trajectory CSVs)
```

### Key commands

```bash
# Activate environment
wellbeing_env\Scripts\activate

# Rebuild everything (weighted by default)
python make.py clean
python make.py all

# Individual runs
python main.py --level group --england-only         # weighted WLS
python main.py --no-weighting                       # unweighted OLS for comparison
python main.py --no-combine-splits                  # keep splits separate
python maps.py --level supergroup --measure anxiety
python qof_panel.py --pre-covid

# Export curated data (includes SEs)
python make.py curated

# Build paper
cd papers\cohort_description
build.bat
```

## Key findings so far

### Life satisfaction and worthwhile
Convergence pattern: lowest-baseline area types improve most. Ethnically Diverse Metropolitan Living (baseline 7.20) improving fastest. Affluent England (7.53) flat. Services and Industrial Legacy (53 LAs) overwhelmingly stable (98%).

### Happiness
Broad improvement. Services, Manufacturing and Mining Legacy (42 LAs at group level) most consistent: slope 0.012, 19% improving, zero deteriorating. Mining Legacy subgroup (13 LAs) improving at 0.014 with 31% significant. Challenges "left behind" narrative.

### Anxiety
Universal deterioration EXCEPT Ethnically Diverse Metropolitan Living (only improver). Worst hit: Larger Towns and Cities (44% deteriorating), Scottish Countryside (40%), Remoter Coastal Living (35%). Pattern is inverse of regression to mean — low-anxiety rural areas catching up with urban anxiety levels.

### National variation (NEW)
Northern Ireland shows consistent deterioration from high baselines (life sat 7.75→7.57, happiness declining), concentrated in rural areas. Timing spans 2016-2023 (Brexit referendum→implementation). Scotland deteriorates on life satisfaction but improves on happiness. England and Wales track UK-wide patterns. All nations show anxiety worsening, Scotland fastest (+0.024 vs England +0.020).

### Fixed effects model (UTLA level, 127 LAs)
Hypertension prevalence coefficient: -0.024 (p=0.054) — borderline significant, correct direction. Limited by UTLA geography (misses district councils). Needs practice-level QOF aggregated to lower-tier LA.

## Known issues / TODO

### Northamptonshire blank on trajectory maps
**STATUS (Feb 2026)**: PARTIALLY FIXED. North/West Northamptonshire (E06000061, E06000062) exist in ONS data but only have actual values for 2019-2022 (earlier years are NaN placeholders). When combined to NORTHANTS_COMBINED, this yields only 4 years of real data (< 6 year threshold), so no trajectory classification. Same issue affects Dorset and Cumbria splits. These 3 combined counties appear filled on classification maps but white/"no data" on trajectory maps. This is a genuine ONS data limitation (2.2% missing overall), not a code bug. Documented in paper limitations.

### Missing data
2.2% of LA-year observations have missing values (448 of 20,064), concentrated in 2011/12 (5%) and newly-created unitary codes. Pattern is uniform across all 4 measures. Affects 33 LAs total, 6 severely (>50% missing). Does not bias trajectory analysis as long as missingness is not related to trends. Documented in paper Methods section.

### QOF practice-to-LA pipeline
The qof_setup/ directory has PROJECT_SPEC.md with full specification. Pipeline needs end-to-end testing with actual NHS Digital downloads.

### Paper compilation
LaTeX paper in papers/cohort_description/paper_revised.tex. Updated with: national comparison section, manual classification rationale, weighted methods discussion, temporal alignment guidance, evaluation framing, Brexit hypothesis. Needs TinyTeX with standard packages. Build with build.bat from that directory.

## Design decisions made

1. **Boundary harmonisation for true mergers**: aggregate UP to post-merger geography using population-weighted means, processed chronologically for nested mergers (6 mergers: East Suffolk, West Suffolk, Somerset W&T, Buckinghamshire, North Yorkshire, Somerset)

2. **Split authority handling**: Counties abolished and replaced by multiple unitaries (Dorset 2019, Northamptonshire 2021, Cumbria 2023) are combined BACK to their original footprint by default using equal-weighted aggregation via combine_splits() function. This maintains panel balance (354 LAs with full 12-year series vs 351 LAs with 6 exclusions if --no-combine-splits used). ONS publishes split codes with only 1-4 years of actual data (rest are NaN placeholders) and does not publish predecessor districts.

3. **Trajectory classification**: OLS/WLS slope > 0.02, p < 0.1. Anxiety reversed. Thresholds are configurable.

4. **Area classification for merged LAs**: largest predecessor's classification used when predecessors span different supergroups; for combined splits, manual assignments based on county character: Dorset→Countryside Living (predominantly rural despite BCP urban area), Northamptonshire→Urban Settlements (4/7 predecessors Urban), Cumbria→Countryside Living (Lake District character despite Barrow industrial legacy). Documented in SPLIT_CLASSIFICATIONS dict with rationale field.

5. **Scottish code remapping**: S12000015 to S12000047 (Fife), S12000024 to S12000048 (Perth & Kinross), S12000046 to S12000049 (Glasgow), S12000044 to S12000050 (N Lanarkshire)

6. **Cornwall/Scilly**: classification file has "E06000052/E06000053" as combined code, split into two rows in remap function

7. **Output structure**: output/{level}/tables|plots|maps with --england-only suffix

8. **QOF panel**: auto-detects qof_*_la.csv (practice-aggregated) over qof_*_utla.csv (Fingertips), always combines splits for balanced panel analysis

9. **Precision weighting (NEW - Feb 2026)**: Default uses WLS with inverse-variance weights (w = 1/se²) derived from ONS published confidence intervals. Standard errors extracted from CI bounds: se = (upper - lower)/(2×1.96). Validates SEs (must be positive). Falls back to OLS if SEs invalid or --no-weighting flag used. Method choice documented in 'method' column of trajectory results. Enables evaluation-ready estimates with proper precision accounting.

## Peter's research context

Peter is a health economist at Northumbria University who teaches causal inference to doctoral students. This project supports an ECR and aims to produce a publishable data cohort paper with enhanced methodological framing. Peter emphasises:
- Pedagogical value (teaching panel methods through real data)
- The framing: well-being partly derived from health environment, trajectories as hypothesis-generating
- Evaluation readiness: dataset enables DiD and fixed effects evaluation of place-based policies
- Clustering validation: significant clustering by ONS classification supports parallel trends assumption
- The dataset itself (harmonised well-being panel + QOF linkage potential) is a contribution worth publishing
- Target journals: Int J Population Data Science, Health & Place, Social Indicators Research, BMJ Open

## Environment

- Windows PC, Python 3.12, virtual environment (wellbeing_env)
- Pandoc installed (for document conversion)
- TinyTeX installed (for LaTeX)
- No MS Office — uses pandoc for conversion, LaTeX for papers
- Network: standard internet access (ONS, NHS Digital, Fingertips, GitHub)
