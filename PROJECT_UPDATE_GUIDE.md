# Guide: Updating Claude Project Files After Weighted Analysis Implementation

## What Changed (February 2026)

Major update: Implemented **weighted least squares (WLS)** as default estimation method, with inverse-variance weights derived from ONS confidence intervals.

## Files to Upload/Replace in Your Claude Project

### 1. Python Code Files (replace existing versions):
- **data_loading.py** - Extracts SEs from CI bounds
- **analysis.py** - Implements WLS, Newey-West option
- **main.py** - Added --no-weighting flag, default weighted
- **boundaries.py** - SPLIT_CLASSIFICATIONS with rationale
- **maps.py** - combine_boundary_splits() for geometry
- **qof_panel.py** - Always combines splits
- **export_curated.py** - Exports with SEs

### 2. Documentation Files (replace existing versions):
- **PROJECT_BRIEFING.md** → Use PROJECT_BRIEFING_UPDATED.md
- **README.md** → Add precision weighting section
- **IMPLEMENTATION_SUMMARY.md** → Add WLS section
- **paper_revised.tex** → Latest version with national comparison, weighted methods

### 3. New Files to Add:
- **compare_nations.py** - National comparison analysis
- Any diagnostic scripts you found useful

## What to Update in Project Instructions (Custom Instructions)

Your project currently has custom instructions. Add this section:

### Precision Weighting (Feb 2026)

```
The analysis now uses weighted least squares (WLS) by default:
- Standard errors extracted from ONS confidence intervals
- Weights: w = 1/se² (inverse-variance)
- Formula: β = (X'WX)^-1 X'Wy  
- Falls back to OLS if SEs unavailable
- Use --no-weighting flag for unweighted OLS

This is the DEFAULT because:
- Aligns with ONS quality methodology
- Evaluation-ready (DiD designs need precision-weighted estimates)
- More efficient slope estimates
- Critical for multi-dataset linkage

Unweighted OLS available for transparency/comparison via --no-weighting flag.
Results are qualitatively similar but weighted is methodologically preferred.
```

### Update the "Boundary Handling" section:

```
**County split classifications (manual assignments):**
- DORSET_COMBINED → Countryside Living (predominantly rural)
- NORTHANTS_COMBINED → Urban Settlements (4/7 predecessors)
- CUMBRIA_COMBINED → Countryside Living (Lake District character)

Rationale: Based on geographic character rather than population weighting.
Documented in SPLIT_CLASSIFICATIONS dictionary in boundaries.py.
```

### Update "Known Issues":

```
**Northamptonshire/Dorset/Cumbria trajectory gaps (EXPLAINED Feb 2026):**
These county splits have only 4 years of actual data (2019-2022) despite 12-year row structure. ONS backfilled codes with NaN placeholders for 2011-2018. When combined, insufficient data for trajectory analysis (< 6 year threshold). Appear filled on classification maps but white on trajectory maps. This is an ONS data limitation (2.2% missing overall), not a code bug. Affects 6 LAs. Documented in paper.
```

## Critical Code Changes Summary

### data_loading.py
```python
# NEW: Extract SEs from CI
df['se'] = (df['ci_upper'] - df['ci_lower']) / (2 * 1.96)
```

### analysis.py
```python
# NEW: WLS implementation
def compute_la_trends(df, measure, min_years=6, weighted=True):
    if weighted and 'se' in grp.columns:
        w = 1 / (se_vals ** 2)  # Inverse-variance weights
        # WLS formula...
```

### main.py
```python
# NEW: Weighted by default
parser.add_argument('--no-weighting', action='store_true')
trends = compute_la_trends(wb_df, measure, weighted=not args.no_weighting)
```

## Testing After Update

```bash
# Test SE extraction
python -c "from data_loading import load_wellbeing_data; wb = load_wellbeing_data()"
# Should print: "Extracted standard errors from CIs (XXXX valid)"

# Test weighted analysis
python main.py --level supergroup
# Should print: "Estimation: WLS (inverse-variance)"

# Compare weighted vs unweighted
python main.py --level supergroup --no-weighting
# Should show similar but slightly different results
```

## What This Achieves

✅ **Methodologically stronger** - respects survey precision  
✅ **Evaluation-ready** - proper weighting for causal inference  
✅ **Aligns with ONS quality practice** - uses published CIs  
✅ **Transparent** - unweighted still available for comparison  
✅ **Documented** - method choice shown in output  

## Next Steps

1. Copy all updated Python files to project directory
2. Run `python make.py clean && python make.py all`
3. Verify new reports show "WLS" in method column
4. Check results are qualitatively similar to unweighted
5. Update Claude Project knowledge with these files
6. Update paper with weighted results
7. Run sensitivity check with --no-weighting
8. Export curated data with SEs: `python make.py curated`
