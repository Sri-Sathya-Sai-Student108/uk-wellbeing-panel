"""
Trajectory analysis with WLS and optional Newey-West HAC clustering.

Key function: compute_la_trends(df, measure, min_years=6, weighted=True, hac=False)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats
import os
from config import MEASURES, MEASURE_LABELS


def compute_la_trends(df, measure='life-satisfaction', min_years=6, weighted=True, hac=False):
    """
    Compute OLS or WLS slope for each LA, optionally with Newey-West HAC SEs.
    
    Parameters:
    -----------
    df : DataFrame
        Wellbeing data with 'la_code', 'year', 'value', optionally 'se'
    measure : str
        Which wellbeing measure to analyze
    min_years : int
        Minimum years required for trend fitting
    weighted : bool
        If True and 'se' exists, use WLS with w = 1/se²
    hac : bool
        If True, use Newey-West HAC SEs (autocorrelation-robust)
        Requires statsmodels, falls back gracefully if unavailable
    """
    subset = df[df['measure'] == measure].copy()
    results = []

    for la_code, grp in subset.groupby('la_code'):
        grp = grp.dropna(subset=['value']).sort_values('year')
        if len(grp) < min_years:
            continue

        x, y = grp['year'].values, grp['value'].values
        
        # Check if weighting requested and possible
        use_weights = weighted and 'se' in grp.columns
        
        if use_weights:
            se_vals = grp['se'].values
            valid_se = ~np.isnan(se_vals) & (se_vals > 0)
            
            if valid_se.sum() >= min_years:
                x_wls = x[valid_se]
                y_wls = y[valid_se]
                w = 1 / (se_vals[valid_se] ** 2)
                
                # Try WLS with optional HAC using statsmodels
                if hac:
                    try:
                        import statsmodels.api as sm
                        
                        # Prepare data for statsmodels
                        X_sm = sm.add_constant(x_wls)
                        
                        # Fit WLS
                        wls_model = sm.WLS(y_wls, X_sm, weights=w)
                        
                        # Get HAC (Newey-West) covariance
                        wls_result = wls_model.fit(cov_type='HAC', 
                                                   cov_kwds={'maxlags': min(2, len(x_wls)//4)})
                        
                        intercept = wls_result.params[0]
                        slope = wls_result.params[1]
                        se_slope = wls_result.bse[1]
                        p_val = wls_result.pvalues[1]
                        r_squared = wls_result.rsquared
                        
                        method = 'WLS+HAC'
                        
                    except (ImportError, Exception) as e:
                        # Statsmodels unavailable or failed, use manual WLS
                        hac = False  # Fall through to manual WLS below
                
                if not hac:
                    # Manual WLS without HAC
                    X = np.column_stack([np.ones(len(x_wls)), x_wls])
                    W = np.diag(w)
                    
                    try:
                        beta = np.linalg.inv(X.T @ W @ X) @ X.T @ W @ y_wls
                        intercept, slope = beta[0], beta[1]
                        
                        y_pred = intercept + slope * x_wls
                        resid = y_wls - y_pred
                        sse = np.sum(w * resid**2)
                        sst = np.sum(w * (y_wls - np.average(y_wls, weights=w))**2)
                        r_squared = 1 - (sse / sst) if sst > 0 else 0
                        
                        dof = len(x_wls) - 2
                        sigma2 = sse / dof if dof > 0 else 0
                        var_beta = np.linalg.inv(X.T @ W @ X) * sigma2
                        se_slope = np.sqrt(var_beta[1, 1])
                        
                        t_stat = slope / se_slope if se_slope > 0 else 0
                        p_val = 2 * (1 - stats.t.cdf(abs(t_stat), dof))
                        
                        method = 'WLS'
                        
                    except np.linalg.LinAlgError:
                        slope, intercept, r_val, p_val, se_slope = stats.linregress(x, y)
                        r_squared = r_val ** 2
                        method = 'OLS (WLS failed)'
            else:
                # Insufficient valid SEs
                slope, intercept, r_val, p_val, se_slope = stats.linregress(x, y)
                r_squared = r_val ** 2
                method = 'OLS (insufficient SEs)'
        else:
            # Unweighted OLS
            slope, intercept, r_val, p_val, se_slope = stats.linregress(x, y)
            r_squared = r_val ** 2
            method = 'OLS'

        results.append({
            'la_code': la_code,
            'la_name': grp['la_name'].iloc[0] if 'la_name' in grp.columns else '',
            'slope': slope, 'intercept': intercept,
            'r_squared': r_squared, 'p_value': p_val, 'std_err': se_slope,
            'start_value': y[0], 'end_value': y[-1],
            'total_change': y[-1] - y[0],
            'n_years': len(grp),
            'year_start': int(x[0]), 'year_end': int(x[-1]),
            'method': method
        })

    return pd.DataFrame(results)
def classify_trajectories(trends_df, slope_threshold=0.02, p_threshold=0.1):
    """Classify as Improving / Stable / Deteriorating."""
    df = trends_df.copy()
    conditions = [
        (df['slope'] > slope_threshold) & (df['p_value'] < p_threshold),
        (df['slope'] < -slope_threshold) & (df['p_value'] < p_threshold),
    ]
    df['trajectory'] = np.select(conditions,
                                  ['Improving', 'Deteriorating'],
                                  default='Stable')
    return df


def analyse_by_group(trends_df, class_df, group_col='supergroup'):
    """Merge with classification and summarise by the chosen grouping."""
    merged = trends_df.merge(class_df, on='la_code', how='inner')
    if len(merged) == 0 or group_col not in merged.columns:
        print(f"  WARNING: No matches or '{group_col}' column not found.")
        return None

    # Drop rows where the grouping is missing
    merged = merged.dropna(subset=[group_col])
    print(f"  Matched {len(merged)} LAs")

    summary = merged.groupby(group_col).agg(
        n_las=('la_code', 'count'),
        mean_baseline=('start_value', 'mean'),
        mean_slope=('slope', 'mean'),
        median_slope=('slope', 'median'),
        std_slope=('slope', 'std'),
        mean_change=('total_change', 'mean'),
        pct_improving=('trajectory',
                       lambda x: (x == 'Improving').mean() * 100),
        pct_deteriorating=('trajectory',
                           lambda x: (x == 'Deteriorating').mean() * 100),
        pct_stable=('trajectory',
                    lambda x: (x == 'Stable').mean() * 100),
    ).round(3)

    return merged, summary


def test_group_differences(trends_df, class_df, group_col='supergroup'):
    """Kruskal-Wallis + pairwise Mann-Whitney with Bonferroni."""
    merged = trends_df.merge(class_df[['la_code', group_col]],
                             on='la_code', how='inner')
    merged = merged.dropna(subset=[group_col])
    groups = [g['slope'].dropna().values
              for _, g in merged.groupby(group_col)]
    names = [n for n, _ in merged.groupby(group_col)]

    if len(groups) < 2:
        return

    stat, p = stats.kruskal(*groups)
    print(f"\n  Kruskal-Wallis: H={stat:.2f}, p={p:.4f}")

    if p < 0.05:
        n_comp = len(names) * (len(names) - 1) / 2
        print("  Significant pairwise comparisons (Bonferroni):")
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if len(groups[i]) > 1 and len(groups[j]) > 1:
                    _, pv = stats.mannwhitneyu(
                        groups[i], groups[j], alternative='two-sided')
                    adj = min(pv * n_comp, 1.0)
                    if adj < 0.05:
                        print(f"    {names[i][:30]:30s} vs "
                              f"{names[j][:30]:30s}: p={adj:.4f} *")


# ---- Plots ----

def plot_trajectories(wb_df, class_df, measure, group_col='supergroup',
                      output_dir='output'):
    """Time series of mean scores by group with 95% CI."""
    sub = wb_df[wb_df['measure'] == measure].merge(
        class_df[['la_code', group_col]], on='la_code', how='inner')
    sub = sub.dropna(subset=[group_col])
    if len(sub) == 0:
        return

    sg = sub.groupby([group_col, 'year'])['value'].agg(
        ['mean', 'std', 'count']).reset_index()
    sg['se'] = sg['std'] / np.sqrt(sg['count'])

    n_groups = sg[group_col].nunique()
    fig, ax = plt.subplots(figsize=(14, max(8, n_groups * 0.8)))
    colours = plt.cm.tab20(np.linspace(0, 1, max(n_groups, 2)))

    for i, (name, g) in enumerate(sg.groupby(group_col)):
        g = g.sort_values('year')
        ax.plot(g['year'], g['mean'], '-o', color=colours[i],
                label=name, linewidth=2, markersize=3)
        ax.fill_between(g['year'], g['mean'] - 1.96 * g['se'],
                        g['mean'] + 1.96 * g['se'],
                        color=colours[i], alpha=0.08)

    ax.axvspan(2019.5, 2020.5, alpha=0.15, color='red', label='COVID')
    ax.set_xlabel('Year')
    ax.set_ylabel(f'Mean {MEASURE_LABELS[measure]} Score')
    ax.set_title(f'{MEASURE_LABELS[measure]} by {group_col.title()}, '
                 f'2011/12-2022/23')
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'trajectories_{measure}.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: trajectories_{measure}.png")


def plot_slopes(trends_df, class_df, measure, group_col='supergroup',
                output_dir='output'):
    """Box plot of slopes by group."""
    m = trends_df.merge(class_df[['la_code', group_col]],
                        on='la_code', how='inner')
    m = m.dropna(subset=[group_col])
    if len(m) == 0:
        return

    fig_width = max(12, m[group_col].nunique() * 0.8)
    fig, ax = plt.subplots(figsize=(fig_width, 6))
    order = m.groupby(group_col)['slope'].median().sort_values().index
    data = [m[m[group_col] == s]['slope'].dropna().values for s in order]
    bp = ax.boxplot(data, labels=[s[:25] for s in order], patch_artist=True)

    cols = plt.cm.RdYlGn(np.linspace(0.2, 0.8, len(order)))
    for patch, c in zip(bp['boxes'], cols):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)

    ax.axhline(0, color='k', ls='--', lw=0.8, alpha=0.5)
    ax.set_ylabel('Annual Trend (slope)')
    ax.set_title(f'{MEASURE_LABELS[measure]} Trends by {group_col.title()}')
    ax.tick_params(axis='x', rotation=55)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'slopes_{measure}.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: slopes_{measure}.png")


def plot_heatmap(summary_df, measure, group_col='supergroup',
                 output_dir='output'):
    """Heatmap of trajectory percentages by group."""
    if summary_df is None:
        return

    n_rows = len(summary_df)
    fig, ax = plt.subplots(figsize=(10, max(4, n_rows * 0.45)))
    d = summary_df[['pct_improving', 'pct_stable',
                     'pct_deteriorating']].copy()
    d.columns = ['Improving %', 'Stable %', 'Deteriorating %']

    im = ax.imshow(d.values, cmap='RdYlGn', aspect='auto', vmin=0, vmax=100)
    ax.set_xticks(range(3))
    ax.set_xticklabels(d.columns)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([s[:30] for s in d.index])

    for i in range(len(d)):
        for j in range(3):
            v = d.values[i, j]
            ax.text(j, i, f'{v:.0f}%', ha='center', va='center',
                    fontsize=9, fontweight='bold',
                    color='white' if v > 60 or v < 20 else 'black')

    ax.set_title(f'{MEASURE_LABELS[measure]}: Trajectories by '
                 f'{group_col.title()}')
    plt.colorbar(im, ax=ax, label='% of LAs')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'heatmap_{measure}.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: heatmap_{measure}.png")


def plot_four_panel(wb_df, class_df, group_col='supergroup',
                    output_dir='output'):
    """2x2 panel of all four measures."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    n_groups = class_df[group_col].dropna().nunique()
    colours = plt.cm.tab20(np.linspace(0, 1, max(n_groups, 2)))

    for idx, m in enumerate(MEASURES):
        ax = axes[idx // 2][idx % 2]
        sub = wb_df[wb_df['measure'] == m].merge(
            class_df[['la_code', group_col]], on='la_code', how='inner')
        sub = sub.dropna(subset=[group_col])
        if len(sub) == 0:
            continue
        means = sub.groupby([group_col, 'year'])['value'].mean().reset_index()
        for i, (sg, g) in enumerate(means.groupby(group_col)):
            g = g.sort_values('year')
            ax.plot(g['year'], g['value'], '-', color=colours[i], lw=1.5,
                    label=sg if idx == 0 else '')
        ax.axvspan(2019.5, 2020.5, alpha=0.1, color='red')
        ax.set_title(MEASURE_LABELS[m])
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='center right', fontsize=7,
               bbox_to_anchor=(1.2, 0.5))
    fig.suptitle(f'ONS Personal Well-being by {group_col.title()}, '
                 f'2011/12-2022/23', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'four_measures_panel.png'),
                dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: four_measures_panel.png")
