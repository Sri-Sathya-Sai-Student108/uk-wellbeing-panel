"""
QOF data loading and fixed effects panel model.

Pulls QOF prevalence data from Fingertips at UTLA level, merges with the
wellbeing panel, and runs two-way fixed effects models.

Requirements: pip install fingertips_py linearmodels

Usage:
  python qof_panel.py                      # default: hypertension
  python qof_panel.py --qof diabetes       # use diabetes instead
  python qof_panel.py --measure happiness   # different wellbeing outcome
  python qof_panel.py --pre-covid           # restrict to 2012-2019
"""

import argparse
import os
import sys
import warnings
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

from config import DATA_DIR, OUTPUT_DIR, MEASURES, MEASURE_LABELS
from data_loading import check_data_files, load_wellbeing_data, load_area_classification
from boundaries import harmonise_boundaries, propagate_classification, combine_splits

# ============================================================================
# FINGERTIPS QOF INDICATOR IDS
# ============================================================================
# These are stable indicator IDs from the Fingertips API.
# Area type 402 = upper tier local authority (UTLA/county & UA)
# Area type 401 = lower tier local authority (district & UA)
# We use 402 since the wellbeing data is at that level.

QOF_INDICATORS = {
    'hypertension': {
        'indicator_id': 219,
        'label': 'Hypertension QOF prevalence (all ages)',
        'short': 'Hypertension %',
    },
    'diabetes': {
        'indicator_id': 241,
        'label': 'Diabetes QOF prevalence (17+)',
        'short': 'Diabetes %',
    },
}

AREA_TYPE_UTLA = 402


def load_qof_from_fingertips(qof_name='hypertension', cache_path=None):
    """
    Pull QOF prevalence data from Fingertips API at UTLA level.

    Caches to CSV so you only hit the API once.

    Returns DataFrame with: la_code, year, qof_prevalence
    """
    if qof_name not in QOF_INDICATORS:
        print(f"ERROR: Unknown QOF indicator '{qof_name}'. "
              f"Choose from: {list(QOF_INDICATORS.keys())}")
        sys.exit(1)

    ind = QOF_INDICATORS[qof_name]
    indicator_id = ind['indicator_id']
    label = ind['label']

    if cache_path is None:
        cache_path = os.path.join(DATA_DIR, f'qof_{qof_name}_utla.csv')

    if os.path.exists(cache_path):
        print(f"Loading cached QOF data from {cache_path}...")
        df = pd.read_csv(cache_path)
        print(f"  {len(df)} obs, {df['la_code'].nunique()} LAs, "
              f"years {df['year'].min()}-{df['year'].max()}")
        return df

    print(f"Downloading {label} from Fingertips (indicator {indicator_id})...")
    try:
        import fingertips_py as ftp
        raw = ftp.retrieve_data.get_data_by_indicator_ids(
            indicator_ids=[indicator_id],
            area_type_id=AREA_TYPE_UTLA
        )
    except ImportError:
        print("ERROR: fingertips_py not installed. Run: pip install fingertips_py")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR downloading from Fingertips: {e}")
        print("You may need to download manually Ã¢â‚¬â€ see README.")
        sys.exit(1)

    print(f"  Raw data: {len(raw)} rows")
    print(f"  Columns: {list(raw.columns)}")

    # Filter to the prevalence values
    # Fingertips returns Value, Area Code, Time period, Sex, Age
    df = raw[['Area Code', 'Time period', 'Value']].copy()
    df = df.rename(columns={
        'Area Code': 'la_code',
        'Time period': 'period',
        'Value': 'qof_prevalence'
    })

    # Extract year from period (e.g. '2022/23' -> 2022)
    df['year'] = df['period'].str[:4].astype(int)

    # Filter to LA-level codes
    df = df[df['la_code'].str.match(r'^E\d{2}', na=False)]
    df = df.dropna(subset=['qof_prevalence'])

    # Keep one row per LA per year (there can be duplicates from sex/age)
    df = df.groupby(['la_code', 'year']).agg(
        qof_prevalence=('qof_prevalence', 'first'),
        period=('period', 'first')
    ).reset_index()

    # Cache
    df.to_csv(cache_path, index=False)
    print(f"  Cached to {cache_path}")
    print(f"  {len(df)} obs, {df['la_code'].nunique()} LAs, "
          f"years {df['year'].min()}-{df['year'].max()}")

    return df


def load_qof_from_csv(filepath):
    """
    Load QOF data from a manually downloaded CSV.

    Expected columns: la_code (or Area Code), year (or Time period),
    qof_prevalence (or Value)
    """
    print(f"Loading QOF data from {filepath}...")
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()

    # Try to standardise columns
    rename = {}
    for c in df.columns:
        cl = c.lower()
        if 'area' in cl and 'code' in cl:
            rename[c] = 'la_code'
        elif cl in ['value', 'prevalence', 'qof_prevalence']:
            rename[c] = 'qof_prevalence'
        elif cl in ['time period', 'period', 'year']:
            rename[c] = 'period'
    df = df.rename(columns=rename)

    if 'year' not in df.columns and 'period' in df.columns:
        df['year'] = df['period'].astype(str).str[:4].astype(int)

    df['qof_prevalence'] = pd.to_numeric(df['qof_prevalence'], errors='coerce')
    df = df.dropna(subset=['qof_prevalence'])

    print(f"  {len(df)} obs")
    return df[['la_code', 'year', 'qof_prevalence']].copy()


# ============================================================================
# PANEL CONSTRUCTION
# ============================================================================

def build_panel(wb_df, qof_df, measure='life-satisfaction',
                pre_covid_only=False):
    """
    Merge wellbeing and QOF data into a balanced-ish panel.

    Returns DataFrame with: la_code, year, wellbeing, qof_prevalence,
    baseline_wellbeing, baseline_qof
    """
    # Filter wellbeing to chosen measure
    wb = wb_df[wb_df['measure'] == measure][['la_code', 'year', 'value']].copy()
    wb = wb.rename(columns={'value': 'wellbeing'})

    # Merge
    panel = wb.merge(qof_df[['la_code', 'year', 'qof_prevalence']],
                     on=['la_code', 'year'], how='inner')

    if pre_covid_only:
        panel = panel[panel['year'] <= 2019]

    # Add baseline values (first available year per LA)
    baselines = panel.groupby('la_code').agg(
        baseline_wellbeing=('wellbeing', 'first'),
        baseline_qof=('qof_prevalence', 'first'),
        first_year=('year', 'min')
    ).reset_index()

    panel = panel.merge(baselines[['la_code', 'baseline_wellbeing',
                                    'baseline_qof']], on='la_code')

    # Drop LAs with too few years
    counts = panel.groupby('la_code').size()
    keep = counts[counts >= 4].index
    panel = panel[panel['la_code'].isin(keep)]

    print(f"\n  Panel: {panel['la_code'].nunique()} LAs, "
          f"{len(panel)} obs, years {panel['year'].min()}-{panel['year'].max()}")

    return panel


# ============================================================================
# FIXED EFFECTS MODEL
# ============================================================================

def run_fixed_effects(panel, output_dir='output'):
    """
    Two-way fixed effects: wellbeing_it = alpha_i + gamma_t + beta*QOF_it + e_it

    Uses linearmodels.PanelOLS if available, otherwise statsmodels with dummies.
    """
    print("\n" + "=" * 60)
    print("FIXED EFFECTS PANEL MODEL")
    print("=" * 60)

    # Set up panel index
    panel = panel.copy()
    panel['la_code_cat'] = pd.Categorical(panel['la_code'])
    panel['year_cat'] = pd.Categorical(panel['year'])

    try:
        from linearmodels.panel import PanelOLS
        import linearmodels

        # linearmodels needs a MultiIndex
        pdata = panel.set_index(['la_code', 'year'])

        mod = PanelOLS(
            dependent=pdata['wellbeing'],
            exog=pdata[['qof_prevalence']],
            entity_effects=True,
            time_effects=True,
            check_rank=False
        )
        res = mod.fit(cov_type='clustered', cluster_entity=True)

        print(res.summary)

        # Save results
        results_path = os.path.join(output_dir, 'fe_model_results.txt')
        with open(results_path, 'w') as f:
            f.write(str(res.summary))
            f.write("\n\nInterpretation:\n")
            f.write("The coefficient on QOF prevalence shows the within-LA\n")
            f.write("association: when QOF prevalence rises by 1pp within\n")
            f.write("an LA (relative to its own mean), wellbeing changes\n")
            f.write("by [coefficient] points on the 0-10 scale.\n")
            f.write("\nLA fixed effects absorb all time-invariant differences.\n")
            f.write("Year fixed effects absorb national shocks (COVID etc).\n")
            f.write("Standard errors clustered at LA level.\n")
        print(f"\n  Saved: {results_path}")

        return res

    except ImportError:
        print("  linearmodels not available, using statsmodels OLS with dummies")
        return _run_fe_statsmodels(panel, output_dir)


def _run_fe_statsmodels(panel, output_dir):
    """Fallback FE using statsmodels with explicit dummies."""
    import statsmodels.api as sm

    # Demean (within transformation) Ã¢â‚¬â€ equivalent to entity FE
    panel = panel.copy()
    for col in ['wellbeing', 'qof_prevalence']:
        panel[f'{col}_dm'] = panel.groupby('la_code')[col].transform(
            lambda x: x - x.mean())

    # Add year dummies for time FE
    year_dummies = pd.get_dummies(panel['year'], prefix='yr', drop_first=True,
                                  dtype=float)
    # Demean year dummies too
    for c in year_dummies.columns:
        year_dummies[c] = panel.groupby('la_code')[c if c in panel.columns
                                                     else year_dummies[c].name].transform(
            lambda x: x - x.mean()) if c in panel.columns else year_dummies[c]

    X = pd.concat([panel[['qof_prevalence_dm']], year_dummies], axis=1)
    X = sm.add_constant(X)
    y = panel['wellbeing_dm']

    model = sm.OLS(y, X).fit(cov_type='cluster',
                              cov_kwds={'groups': panel['la_code']})
    print(model.summary())

    results_path = os.path.join(output_dir, 'fe_model_results.txt')
    with open(results_path, 'w') as f:
        f.write(str(model.summary()))
    print(f"\n  Saved: {results_path}")

    return model


# ============================================================================
# DESCRIPTIVE PANEL PLOTS
# ============================================================================

def plot_baseline_vs_slope(panel, class_df, measure, group_col='supergroup',
                           output_dir='output'):
    """Scatter: baseline wellbeing vs slope, coloured by area type."""
    import matplotlib.pyplot as plt

    # Compute slopes
    slopes = []
    for la, grp in panel.groupby('la_code'):
        grp = grp.sort_values('year')
        if len(grp) < 4:
            continue
        s, _, _, _, _ = stats.linregress(grp['year'], grp['wellbeing'])
        slopes.append({
            'la_code': la,
            'slope': s,
            'baseline': grp['wellbeing'].iloc[0]
        })
    slopes_df = pd.DataFrame(slopes)

    merged = slopes_df.merge(class_df[['la_code', group_col]],
                              on='la_code', how='inner')
    merged = merged.dropna(subset=[group_col])

    fig, ax = plt.subplots(figsize=(12, 8))
    groups = merged[group_col].unique()
    colours = plt.cm.tab20(np.linspace(0, 1, max(len(groups), 2)))

    for i, g in enumerate(sorted(groups)):
        sub = merged[merged[group_col] == g]
        ax.scatter(sub['baseline'], sub['slope'], c=[colours[i]],
                   label=g, alpha=0.7, s=40)

    ax.axhline(0, color='k', ls='--', lw=0.8, alpha=0.5)
    ax.set_xlabel(f'Baseline {MEASURE_LABELS.get(measure, measure)} (first year)')
    ax.set_ylabel('Annual Slope')
    ax.set_title(f'Baseline vs Trajectory: {MEASURE_LABELS.get(measure, measure)}')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    # Add regression line
    x, y = merged['baseline'].values, merged['slope'].values
    m, b, r, p, _ = stats.linregress(x, y)
    xline = np.linspace(x.min(), x.max(), 100)
    ax.plot(xline, m * xline + b, 'r-', lw=1.5, alpha=0.6,
            label=f'r={r:.3f}, p={p:.3f}')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'baseline_vs_slope_{measure}.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: baseline_vs_slope_{measure}.png")


def plot_qof_vs_wellbeing_scatter(panel, class_df, measure,
                                   group_col='supergroup',
                                   output_dir='output'):
    """Scatter of QOF change vs wellbeing change by LA."""
    import matplotlib.pyplot as plt

    changes = []
    for la, grp in panel.groupby('la_code'):
        grp = grp.sort_values('year')
        if len(grp) < 4:
            continue
        sw, _, _, _, _ = stats.linregress(grp['year'], grp['wellbeing'])
        sq, _, _, _, _ = stats.linregress(grp['year'], grp['qof_prevalence'])
        changes.append({'la_code': la, 'wb_slope': sw, 'qof_slope': sq})

    changes_df = pd.DataFrame(changes)
    merged = changes_df.merge(class_df[['la_code', group_col]],
                               on='la_code', how='inner')
    merged = merged.dropna(subset=[group_col])

    fig, ax = plt.subplots(figsize=(12, 8))
    groups = merged[group_col].unique()
    colours = plt.cm.tab20(np.linspace(0, 1, max(len(groups), 2)))

    for i, g in enumerate(sorted(groups)):
        sub = merged[merged[group_col] == g]
        ax.scatter(sub['qof_slope'], sub['wb_slope'], c=[colours[i]],
                   label=g, alpha=0.7, s=40)

    ax.axhline(0, color='k', ls='--', lw=0.5, alpha=0.5)
    ax.axvline(0, color='k', ls='--', lw=0.5, alpha=0.5)

    x, y = merged['qof_slope'].values, merged['wb_slope'].values
    m, b, r, p, _ = stats.linregress(x, y)
    xline = np.linspace(x.min(), x.max(), 100)
    ax.plot(xline, m * xline + b, 'r-', lw=1.5, alpha=0.6)

    ax.set_xlabel(f'QOF Prevalence Slope (pp/year)')
    ax.set_ylabel(f'{MEASURE_LABELS.get(measure, measure)} Slope (pts/year)')
    ax.set_title(f'QOF Trend vs Wellbeing Trend (r={r:.3f}, p={p:.3f})')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'qof_vs_wellbeing_{measure}.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: qof_vs_wellbeing_{measure}.png")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='QOF + Wellbeing Fixed Effects Panel')
    parser.add_argument('--qof', choices=['hypertension', 'diabetes'],
                        default='hypertension',
                        help='QOF indicator to use')
    parser.add_argument('--measure', choices=MEASURES,
                        default='life-satisfaction',
                        help='Wellbeing measure as dependent variable')
    parser.add_argument('--pre-covid', action='store_true',
                        help='Restrict to pre-COVID period (<=2019)')
    parser.add_argument('--level', choices=['supergroup', 'group', 'subgroup'],
                        default='supergroup',
                        help='Area classification level for plots')
    parser.add_argument('--include-ni', action='store_true',
                        help='Include Northern Ireland (requires NI QOF data '
                             'in data/qof_ni_<indicator>.csv)')
    args = parser.parse_args()

    out_dir = os.path.join(OUTPUT_DIR, 'qof_panel')
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    print("=" * 60)
    print(f"QOF PANEL ANALYSIS")
    print(f"  QOF indicator: {args.qof}")
    print(f"  Wellbeing measure: {MEASURE_LABELS[args.measure]}")
    print(f"  Pre-COVID only: {args.pre_covid}")
    print(f"  Include NI: {args.include_ni}")
    print("=" * 60)

    if not check_data_files():
        return

    # Load wellbeing data
    wb_df = load_wellbeing_data()
    wb_df = harmonise_boundaries(wb_df)
    
    # Combine county splits to maintain historic geography for linkage
    # (Always done in panel analysis - no flag)
    wb_df = combine_splits(wb_df)

    # QOF applies in England (via Fingertips) and Northern Ireland (separate).
    # Default is England-only. --include-ni adds NI if data is available.
    country_codes = ['E']
    scope = "England"
    if args.include_ni:
        country_codes.append('N')
        scope = "England + Northern Ireland"

    wb_df = wb_df[wb_df['la_code'].str.startswith(tuple(country_codes))]
    print(f"  Filtered to {scope}: {wb_df['la_code'].nunique()} LAs")

    # Load classification
    class_df = load_area_classification()
    class_df = propagate_classification(class_df)
    class_df = combine_splits(class_df)
    class_df = class_df[class_df['la_code'].str.startswith(tuple(country_codes))]

    # Load QOF data Ã¢â‚¬â€ England from Fingertips
    cache = os.path.join(DATA_DIR, f'qof_{args.qof}_utla.csv')
    if os.path.exists(cache):
        qof_df = load_qof_from_csv(cache)
    else:
        qof_df = load_qof_from_fingertips(args.qof, cache_path=cache)

    # If including NI, look for a separate NI QOF file and append
    if args.include_ni:
        ni_path = os.path.join(DATA_DIR, f'qof_ni_{args.qof}.csv')
        if os.path.exists(ni_path):
            ni_df = load_qof_from_csv(ni_path)
            qof_df = pd.concat([qof_df, ni_df], ignore_index=True)
            print(f"  Added NI QOF data: {ni_df['la_code'].nunique()} LAs")
        else:
            print(f"  WARNING: --include-ni specified but {ni_path} not found.")
            print(f"  Download NI QOF data from:")
            print(f"    https://www.health-ni.gov.uk/articles/"
                  f"quality-and-outcomes-framework-statistics")
            print(f"  Save as {ni_path} with columns: la_code, year, qof_prevalence")
            print(f"  NI LA codes are N09000001 to N09000011")
            print(f"  Proceeding with England only.")

    # Build panel
    panel = build_panel(wb_df, qof_df, measure=args.measure,
                        pre_covid_only=args.pre_covid)

    if len(panel) == 0:
        print("ERROR: Empty panel after merge. Check LA codes match.")
        return

    # Descriptive stats
    print(f"\nDescriptive statistics:")
    print(panel[['wellbeing', 'qof_prevalence']].describe().round(3))

    # Correlation
    r, p = stats.pearsonr(panel['wellbeing'], panel['qof_prevalence'])
    print(f"\nPooled correlation: r={r:.3f}, p={p:.4f}")
    print("(This mixes between-LA and within-LA variation Ã¢â‚¬â€ the FE model"
          " isolates the within-LA relationship)")

    # Run fixed effects model
    import matplotlib
    matplotlib.use('Agg')

    result = run_fixed_effects(panel, output_dir=out_dir)

    # Plots
    print("\nGenerating plots...")
    group_col = args.level
    if group_col in class_df.columns:
        plot_baseline_vs_slope(panel, class_df, args.measure,
                               group_col=group_col, output_dir=out_dir)
        plot_qof_vs_wellbeing_scatter(panel, class_df, args.measure,
                                      group_col=group_col, output_dir=out_dir)
    else:
        print(f"  Skipping plots: '{group_col}' not in classification data")

    # Save panel data for inspection
    panel_path = os.path.join(out_dir, 'panel_data.csv')
    panel.to_csv(panel_path, index=False)
    print(f"  Panel data: {panel_path}")

    print(f"\n{'=' * 60}")
    print(f"DONE. Outputs in {out_dir}/")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
