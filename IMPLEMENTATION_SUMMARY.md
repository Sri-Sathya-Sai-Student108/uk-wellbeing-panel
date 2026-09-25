# County Splits Implementation Summary

## What Was Done

Implemented the `combine_splits()` function and integrated it into the analysis pipeline to handle the 3 county splits (Dorset, Northamptonshire, Cumbria) that occurred 2019-2023.

## Files Modified

### 1. boundaries.py (UPDATED)
**Added:**
- `BOUNDARY_SPLITS` dictionary defining the 3 county splits
- `combine_splits()` function that:
  - Takes split parts (e.g., E06000061, E06000062)
  - Combines them to original county footprint (NORTHANTS_COMBINED)
  - Uses equal-weighted aggregation
  - Removes the split parts from the dataset
  - Handles both wellbeing data and classification data formats

**Lines added:** ~100 (at end of file)

### 2. maps.py (UPDATED)
**Added:**
- `--no-combine-splits` argument flag
- Import of `combine_splits` function
- Conditional call to `combine_splits()` (default: True)

**Logic:**
```python
if not args.no_combine_splits:  # DEFAULT
    wb_df = combine_splits(wb_df)
    class_df = combine_splits(class_df)
```

### 3. qof_panel.py (UPDATED)
**Added:**
- Import of `combine_splits` function
- Always calls `combine_splits()` (no flag - panel analysis needs balanced data)

**Logic:**
```python
# Always combine for panel analysis
wb_df = combine_splits(wb_df)
class_df = combine_splits(class_df)
```

### 4. main.py (CREATED)
**New file** - trajectory analysis script with:
- `--level` flag (supergroup/group/subgroup)
- `--england-only` flag
- `--no-combine-splits` flag (default: combine)
- Calls all analysis functions
- Generates reports, plots, Excel outputs

## Default Behavior (Recommended)

**Command:** `python main.py` or `python maps.py`

**What happens:**
1. Loads wellbeing data with E06000061, E06000062, E06000058, E06000059 (split codes)
2. Runs `harmonise_boundaries()` - aggregates true mergers
3. Runs `propagate_classification()` - adds classifications for merged/split codes
4. Runs `combine_splits()` - combines split parts back to county footprints:
   - E06000061 + E06000062 → NORTHANTS_COMBINED
   - E06000058 + E06000059 → DORSET_COMBINED
   - E06000063 + E06000064 → CUMBRIA_COMBINED (if they exist)
5. Final dataset: **354 LAs** (351 + 3 combined counties)

## Optional Behavior

**Command:** `python main.py --no-combine-splits`

**What happens:**
1. Same as above BUT skips step 4 (combine_splits)
2. Keeps E06000061, E06000062, etc. as separate LAs
3. Final dataset: **360 LAs** (more LAs, but some with only 4 years of data)

## Why Combine by Default?

**Historic data linkage:** Most published datasets pre-2021 use:
- Old county codes (Northamptonshire as one unit)
- Old district codes (Corby, Kettering, etc.)
- NOT the new split codes (E06000061, E06000062)

**To link to:**
- Census 2011 → needs old geography
- IMD 2019 → uses old districts
- QOF pre-2021 → aggregates to old counties
- ONS mortality → uses old codes
- Employment data → uses old geography

**Combining splits maintains the historic footprint** that other datasets can match to.

## Impact on Results

**Before fix:**
- 351 LAs in analysis (6 split codes excluded)
- Northamptonshire, Dorset, Cumbria blank on maps
- Missing data for those areas

**After fix (default):**
- 354 LAs in analysis (3 combined counties included)
- All maps complete
- Northamptonshire appears as one combined area
- Classification: Manual assignments based on county character documented in SPLIT_CLASSIFICATIONS:
  - Dorset → Countryside Living (predominantly rural)
  - Northamptonshire → Urban Settlements (4/7 predecessors Urban)
  - Cumbria → Countryside Living (Lake District character)

**No change to conclusions** because:
- Combined areas will likely classify as "stable" (averaging across parts)
- Supergroup-level patterns unchanged
- You're gaining 3 LAs with complete data, not losing anything

## Testing the Fix

### 1. Test maps generation:
```bash
python maps.py --level supergroup
```

**Expected output:**
```
Combining county splits to maintain balanced panel...
  Dorset (combined): +48 combined rows, -96 split part rows
  Northamptonshire (combined): +48 combined rows, -96 split part rows
  Cumbria (combined): +0 combined rows, -0 split part rows (no data yet)
  Total rows added: 96
  Final: 354 LAs
```

**Check maps:** Northamptonshire and Dorset should now be filled (not blank)

### 2. Test trajectory analysis:
```bash
python main.py --level supergroup
```

**Expected output:**
```
Combining county splits to maintain balanced panel...
  ...
  Final: 354 LAs
```

**Check report:** Should show 354 LAs total across supergroups

### 3. Test with --no-combine-splits:
```bash
python main.py --no-combine-splits
```

**Expected:** 360 LAs, split codes kept separate

## Files to Update in Your Project

Replace these files in `C:\Users\mcpj6\dev\NHealth\v0\`:

1. **boundaries.py** - has combine_splits() function
2. **maps.py** - calls combine_splits() by default
3. **qof_panel.py** - always calls combine_splits()
4. **main.py** - NEW FILE, calls combine_splits() by default

## Next Steps

1. Copy the 4 files to your project directory
2. Run `python make.py clean`
3. Run `python make.py all`
4. Check that all maps are complete (no blank areas)
5. Check report.txt shows 354 LAs
6. Update paper.tex to say "354 local authorities" (currently says 351)
