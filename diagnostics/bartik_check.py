#!/usr/bin/env python3
"""
bartik_check.py - Python sanity check of Bartik IV analysis.

Replicates Radakrishnan et al. (2025) Stata do-file in Python to validate
the panel data pipeline before Rama runs full analysis in Stata.

Sections:
  1. Bartik instrument construction (2016 baseline)
  2. First-stage diagnostics
  3. Main IV outcomes (vacancies, employees, benefits) -- LA level
  4. Regional broad-brush: retail x high/low overseas interaction on
     social care and benefits -- region level (N=9), the ONLY place
     overseas/visa data is used. (Previously duplicated at LA level as
     an "overseas heterogeneity" section, but that used a regional
     share broadcast down with zero LA-to-LA variation -- removed.)
  5. Summary comparison to paper benchmarks

Key checks:
  - First-stage F ~ 43 (paper benchmark)
  - Vacancies: null (beta~0, p>0.05)
  - Benefit claimants rate: negative, significant (beta~-0.495, p<0.05)

Notes:
  - pop_65plus used (paper uses pop_60 -- flagged in output)
  - Excludes City of London (E09000001) and Isles of Scilly (E06000053)
  - Clustered SEs at LA level throughout
  - Two-way FE: LA + year

Usage:
  python bartik_check.py
"""

import os
import warnings
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

import os, sys, warnings
import numpy as np
import pandas as pd
from scipy import stats

# Allow running from diagnostics/ subfolder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from linearmodels.iv import IV2SLS
    from linearmodels.panel import PanelOLS
    HAS_LINEARMODELS = True
except ImportError:
    print("ERROR: linearmodels not installed. Run: pip install linearmodels")
    raise

from config import DATA_DIR, OUTPUT_DIR

SFC_FILE    = os.path.join(DATA_DIR, 'intermediate', 'england_panel_sfc.csv')
PAYE_FILE   = os.path.join(DATA_DIR, 'intermediate', 'paye_overseas_regional.csv')
OUTPUT_DIR  = os.path.join(OUTPUT_DIR, 'bartik')

EXCL = {'E09000001',  # City of London
        'E06000053'}  # Isles of Scilly

YEAR_MIN_ANALYSIS = 2020
YEAR_MAX_ANALYSIS = 2023


# ---------------------------------------------------------------------------
# Load and prepare data
# ---------------------------------------------------------------------------

def load_data():
    """Load SfC panel, exclude tiny LAs, prepare derived variables."""
    df = pd.read_csv(SFC_FILE)

    # Deduplicate -- panel is long on measure; we don't need wellbeing here
    df = df.drop_duplicates(subset=['la_code', 'year']).copy()

    # Exclude City of London and Isles of Scilly
    df = df[~df['la_code'].isin(EXCL)].copy()

    # Derived variables (matching Stata do-file)
    df['posts']        = df['filled_posts'].fillna(0) + df['vacant_posts'].fillna(0)
    df['vacancy_rate'] = np.where(
        df['posts'] > 0,
        (df['vacant_posts'] / df['posts']) * 100,
        np.nan
    )
    # Use December claimants if available (matches Rama), else annual mean
    if 'claimants_december' in df.columns:
        df['benefit_rate'] = df['claimants_december'] / df['pop_total'] * 1000
        print("  Using claimants_december for benefit_rate (matches Rama)")
    else:
        df['benefit_rate'] = df['claimants_mean'] / df['pop_total'] * 1000
        print("  Using claimants_mean for benefit_rate (annual average)")

    # Keep both for comparison
    if 'claimants_annual' in df.columns:
        df['benefit_rate_annual'] = df['claimants_annual'] / df['pop_total'] * 1000
    df['fte_per_emp']  = np.where(
        df['employees'] > 0,
        df['fte_posts'] / df['employees'],
        np.nan
    )

    # Numeric LA index for fixed effects
    df['la_id'] = pd.Categorical(df['la_code']).codes

    print(f"  Panel: {df['la_code'].nunique()} LAs, "
          f"years {df['year'].min()}-{df['year'].max()}")
    print(f"  Excluded: City of London, Isles of Scilly")
    print(f"  NOTE: Using pop_65plus (paper uses pop_60 -- expect minor differences)")

    return df


def load_paye_regional():
    """Load PAYE regional data for mechanism analysis (Section 5)."""
    paye = pd.read_csv(PAYE_FILE)
    # Keep English regions + Scotland
    paye = paye[paye['region_code'].str.startswith(('E12', 'S'), na=False)].copy()
    return paye


# ---------------------------------------------------------------------------
# Section 1: Construct Bartik instrument
# ---------------------------------------------------------------------------

def construct_bartik(df):
    """
    Construct Bartik IV (2016 baseline) following Stata Section 1.

    bartik_iv = share_new_2016 * growth_new_from2016
              + share_old_2016 * growth_old_from2016

    Where growth rates are leave-one-out national totals.
    """
    print("\n" + "=" * 70)
    print("SECTION 1: BARTIK INSTRUMENT CONSTRUCTION")
    print("=" * 70)

    df = df.copy()

    # Step 1: 2016 baseline shares
    base = df[df['year'] == 2016][['la_code', 'tot_new', 'tot_old', 'tot']].copy()
    base = base.rename(columns={
        'tot_new': 'base_new',
        'tot_old': 'base_old',
        'tot':     'base_tot',
    })
    base['share_new_2016'] = base['base_new'] / base['base_tot']
    base['share_old_2016'] = base['base_old'] / base['base_tot']

    # Handle LAs with zero total stores in 2016
    n_zero = (base['base_tot'] == 0).sum()
    if n_zero > 0:
        print(f"  WARNING: {n_zero} LAs have zero stores in 2016 -- Bartik set to NaN")

    df = df.merge(base[['la_code', 'share_new_2016', 'share_old_2016',
                         'base_new', 'base_old', 'base_tot']],
                  on='la_code', how='left')

    # Step 2: National leave-one-out growth rates
    national = df.groupby('year')[['tot_new', 'tot_old']].sum().reset_index()
    national = national.rename(columns={
        'tot_new': 'nat_new',
        'tot_old': 'nat_old',
    })
    df = df.merge(national, on='year')

    # Leave-one-out: subtract own LA
    df['nat_new_excl'] = df['nat_new'] - df['tot_new']
    df['nat_old_excl'] = df['nat_old'] - df['tot_old']

    # 2016 national baseline (leave-one-out)
    base_nat = df[df['year'] == 2016][
        ['la_code', 'nat_new_excl', 'nat_old_excl']
    ].rename(columns={
        'nat_new_excl': 'base_nat_new',
        'nat_old_excl': 'base_nat_old',
    })
    df = df.merge(base_nat, on='la_code', how='left')

    # Growth from 2016 baseline
    df['growth_new'] = (df['nat_new_excl'] - df['base_nat_new']) / df['base_nat_new']
    df['growth_old'] = (df['nat_old_excl'] - df['base_nat_old']) / df['base_nat_old']

    # Step 3: Bartik instrument
    df['bartik'] = (df['share_new_2016'] * df['growth_new'] +
                    df['share_old_2016'] * df['growth_old'])

    # Report 2016 shares
    shares_2016 = base[['share_new_2016']].describe()
    print(f"\n  2016 discount share distribution:")
    print(f"    Mean:   {base['share_new_2016'].mean():.3f}")
    print(f"    Median: {base['share_new_2016'].median():.3f}")
    print(f"    Min:    {base['share_new_2016'].min():.3f}")
    print(f"    Max:    {base['share_new_2016'].max():.3f}")

    # Report Bartik variation in analysis period
    analysis = df[df['year'].between(YEAR_MIN_ANALYSIS, YEAR_MAX_ANALYSIS)]
    print(f"\n  Bartik IV ({YEAR_MIN_ANALYSIS}-{YEAR_MAX_ANALYSIS}) distribution:")
    print(f"    Mean:   {analysis['bartik'].mean():.4f}")
    print(f"    SD:     {analysis['bartik'].std():.4f}")
    print(f"    Min:    {analysis['bartik'].min():.4f}")
    print(f"    Max:    {analysis['bartik'].max():.4f}")

    # Clean up
    drop_cols = ['nat_new', 'nat_old', 'nat_new_excl', 'nat_old_excl',
                 'base_nat_new', 'base_nat_old', 'growth_new', 'growth_old',
                 'base_new', 'base_old', 'base_tot']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    return df


# ---------------------------------------------------------------------------
# IV regression helper
# ---------------------------------------------------------------------------

def run_iv(data, outcome, endog, instrument, controls, entity, time,
           label=''):
    """
    Run 2SLS with entity FE (within demeaning) + year dummies + clustered SEs.
    Pure numpy implementation. Matches:
    Stata: ivreg2 y (x=z) controls i.year, absorb(entity) cluster(entity)
    """
    from numpy.linalg import lstsq

    est = data.dropna(subset=[outcome, endog, instrument] + controls).copy()
    if len(est) == 0:
        print(f"  {label}: no valid observations")
        return None

    # Add year dummies
    yr_dummies = pd.get_dummies(est[time], prefix='yr',
                                 drop_first=True).astype(float)
    yr_cols = yr_dummies.columns.tolist()
    for col in yr_cols:
        est[col] = yr_dummies[col].values

    all_vars = [outcome, endog, instrument] + controls + yr_cols

    # Entity FE: demean all variables by entity
    for col in all_vars:
        est[f'd_{col}'] = (est[col] -
                           est.groupby(entity)[col].transform('mean'))

    clusters = est[entity].values
    unique_c = np.unique(clusters)
    G = len(unique_c)
    n = len(est)

    y  = est[f'd_{outcome}'].values
    Xd = est[f'd_{endog}'].values
    Z  = est[f'd_{instrument}'].values
    C  = np.column_stack([est[f'd_{c}'].values for c in controls + yr_cols] +
                          [np.ones(n)])

    # First stage: endog ~ instrument + controls
    X_fs     = np.column_stack([Z, C])
    b_fs, _, _, _ = lstsq(X_fs, Xd, rcond=None)
    Xd_hat   = X_fs @ b_fs
    res_fs   = Xd - Xd_hat
    k_fs     = X_fs.shape[1]

    meat = np.zeros((k_fs, k_fs))
    for c in unique_c:
        m = clusters == c
        s = X_fs[m].T @ res_fs[m]
        meat += np.outer(s, s)
    V_fs   = (G/(G-1)) * ((n-1)/(n-k_fs)) *              np.linalg.inv(X_fs.T @ X_fs) @ meat @ np.linalg.inv(X_fs.T @ X_fs)
    f_stat = (b_fs[0] / np.sqrt(V_fs[0,0])) ** 2

    # Second stage: y ~ Xd_hat + controls
    X_ss     = np.column_stack([Xd_hat, C])
    b_ss, _, _, _ = lstsq(X_ss, y, rcond=None)
    res_ss   = y - X_ss @ b_ss
    k_ss     = X_ss.shape[1]

    meat2 = np.zeros((k_ss, k_ss))
    for c in unique_c:
        m = clusters == c
        s = X_ss[m].T @ res_ss[m]
        meat2 += np.outer(s, s)
    V_ss   = (G/(G-1)) * ((n-1)/(n-k_ss)) *              np.linalg.inv(X_ss.T @ X_ss) @ meat2 @ np.linalg.inv(X_ss.T @ X_ss)
    se     = np.sqrt(V_ss[0,0])
    t      = b_ss[0] / se
    pval   = 2 * (1 - stats.t.cdf(abs(t), df=G-1))

    class Result:
        pass
    r = Result()
    r.first_stage_f = f_stat
    r.coef    = b_ss[0]
    r.se      = se
    r.pval    = pval
    r.nobs    = n
    r.nclusters = G
    return r

# ---------------------------------------------------------------------------
# Section 2: First stage
# ---------------------------------------------------------------------------

def first_stage(df):
    """
    First stage: tot ~ bartik + controls + LA FE + year FE.
    F-statistic = t-statistic^2 on bartik (single instrument case).
    Uses within-group demeaning equivalent to absorb(la_code).
    """
    print("\n" + "=" * 70)
    print("SECTION 2: FIRST-STAGE DIAGNOSTICS (2020-2023)")
    print("=" * 70)
    print("  Benchmark from paper: F ~ 43")
    print()

    from numpy.linalg import lstsq

    analysis = df[df['year'].between(YEAR_MIN_ANALYSIS,
                                      YEAR_MAX_ANALYSIS)].copy()
    analysis = analysis.dropna(subset=['tot', 'bartik',
                                        'pop_total', 'pop_65plus'])

    # Entity FE: demean by LA
    for col in ['tot', 'bartik', 'pop_total', 'pop_65plus']:
        analysis[f'd_{col}'] = (
            analysis[col] -
            analysis.groupby('la_code')[col].transform('mean')
        )

    # Year dummies - create first, then demean by LA
    yr_dummies = pd.get_dummies(analysis['year'], prefix='yr',
                                 drop_first=True).astype(float)
    yr_cols = yr_dummies.columns.tolist()
    for col in yr_cols:
        analysis[col] = yr_dummies[col].values
        analysis[f'd_{col}'] = (
            analysis[col] -
            analysis.groupby('la_code')[col].transform('mean')
        )

    y = analysis['d_tot'].values
    X = np.column_stack([
        analysis['d_bartik'].values,
        analysis['d_pop_total'].values,
        analysis['d_pop_65plus'].values,
        analysis[[f'd_{c}' for c in yr_cols]].values,
        np.ones(len(analysis))
    ])

    from numpy.linalg import lstsq
    beta, _, _, _ = lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k  = len(y), X.shape[1]

    # Clustered SE for bartik coefficient (cluster by la_code)
    clusters = analysis['la_code'].values
    unique_clusters = np.unique(clusters)
    G = len(unique_clusters)

    meat = np.zeros((k, k))
    for c in unique_clusters:
        mask  = clusters == c
        Xc    = X[mask]
        rc    = resid[mask]
        score = Xc.T @ rc
        meat += np.outer(score, score)

    # Sandwich estimator
    XtX_inv = np.linalg.inv(X.T @ X)
    V_cluster = (G / (G-1)) * ((n-1) / (n-k)) * XtX_inv @ meat @ XtX_inv

    # SE and t-stat for bartik (index 0)
    se_bartik = np.sqrt(V_cluster[0, 0])
    t_stat    = beta[0] / se_bartik
    f_stat    = t_stat ** 2   # F = t^2 for single instrument

    print(f"  First-stage F-statistic: {f_stat:.2f}")
    print(f"  Bartik coefficient:      {beta[0]:.4f}")
    print(f"  Clustered SE:            {se_bartik:.4f}")
    print(f"  Observations:            {n}")
    print(f"  LAs (clusters):          {G}")

    if f_stat >= 16.38:
        print(f"  Strength: STRONG (>16.38 Stock-Yogo 10% threshold)")
    elif f_stat >= 10:
        print(f"  Strength: ADEQUATE (>10 conventional threshold)")
    else:
        print(f"  Strength: WEAK (<10) -- check pipeline")

    return f_stat, beta[0]


# ---------------------------------------------------------------------------
# Section 3: Main IV outcomes
# ---------------------------------------------------------------------------

def main_iv(df):
    """Run IV for all main outcomes. Returns results dict."""
    print("\n" + "=" * 70)
    print("SECTION 3: MAIN IV ANALYSIS (2020-2023)")
    print("=" * 70)

    analysis = df[df['year'].between(YEAR_MIN_ANALYSIS,
                                      YEAR_MAX_ANALYSIS)].copy()
    controls = ['pop_total', 'pop_65plus']

    outcomes = [
        ('vacant_posts',        'Vacant posts',         None, 'Expect: null (~0, p>0.05)'),
        ('vacancy_rate',        'Vacancy rate',         None, 'Expect: null'),
        ('employees',           'Employees',            None, 'Expect: null'),
        ('fte_posts',           'FTE posts',            None, 'Expect: null'),
        ('benefit_rate',        'Benefit rate (Dec)',   None, 'Expect: NEGATIVE, significant (paper: beta~-0.495)'),
    ]
    if 'benefit_rate_annual' in analysis.columns:
        outcomes.append(('benefit_rate_annual', 'Benefit rate (annual)', None,
                         'Expect: positive or null (annual mean)'))

    results = {}
    print()
    print(f"  {'Outcome':<22} {'Coef':>10} {'SE':>8} {'p':>8} "
          f"{'F-stat':>8}  {'Verdict'}")
    print("  " + "-" * 80)

    print("DEBUG: analysis rows:", len(analysis))
    print("DEBUG: vacancy_rate describe:")
    print(analysis['vacancy_rate'].describe())
    print("DEBUG: vacancy_rate == 0 count:", (analysis['vacancy_rate'] == 0).sum())
    print("DEBUG: vacant_posts missing (2020-2023):", analysis['vacant_posts'].isna().sum())
    print("DEBUG: filled_posts missing (2020-2023):", analysis['filled_posts'].isna().sum())
    print("DEBUG: posts <= 0 count:", (analysis['posts'] <= 0).sum())

    for outcome, label, _, note in outcomes:
        r = run_iv(analysis, outcome, 'tot', 'bartik', controls,
                   'la_code', 'year', label)
        if r is None:
            continue

        results[outcome] = r
        sig = '***' if r.pval < 0.01 else '**' if r.pval < 0.05 \
            else '*' if r.pval < 0.10 else ''
        print(f"  {label:<22} {r.coef:>10.3f} {r.se:>8.3f} "
              f"{r.pval:>8.3f} {r.first_stage_f:>8.2f}  {note}")

    return results


# ---------------------------------------------------------------------------
# Section 4 helper: pooled IV with retail x high/low overseas interaction
# ---------------------------------------------------------------------------

def run_iv_region_fe_stage2(data, outcome):
    """
    Stage 1: tot ~ bartik_region + constant ONLY -- no year dummies, no
    region FE, no PAYE. bartik_region is the region-year MEAN of the
    already-computed LA-level bartik instrument (simple average of an
    existing per-LA statistic, not a fresh reconstruction built by
    aggregating LAs into an artificial region total).

    Stage 2: outcome ~ tot_hat (from stage 1) + year dummies +
    overseas_share_contemp (PAYE, CONTEMPORANEOUS year-by-year, not a
    fixed baseline -- see regional_mechanism() docstring for why) +
    region dummies (fixed effects) + constant. Clustered by region.

    This is the agreed design (confirmed multiple times): ONE first
    stage shared across all regions, with region fixed effects and
    PAYE both living in the second stage only.
    """
    needed = [outcome, 'tot', 'bartik_region', 'overseas_share_contemp',
              'region', 'year']
    est = data.dropna(subset=needed).copy()
    if len(est) < 10:
        return None

    clusters = est['region'].values
    unique_c = np.unique(clusters)
    G = len(unique_c)
    n = len(est)

    # --- Stage 1: tot ~ bartik_region + constant ONLY ---
    Z1 = np.column_stack([est['bartik_region'].values, np.ones(n)])
    y_fs = est['tot'].values.astype(float)
    try:
        b_fs, _, _, _ = np.linalg.lstsq(Z1, y_fs, rcond=None)
        tot_hat = Z1 @ b_fs
        res_fs = y_fs - tot_hat
        k1 = Z1.shape[1]
        meat1 = np.zeros((k1, k1))
        for c in unique_c:
            m = clusters == c
            s = Z1[m].T @ res_fs[m]
            meat1 += np.outer(s, s)
        Z1tZ1_inv = np.linalg.inv(Z1.T @ Z1)
        V1 = (G/max(G-1,1)) * ((n-1)/max(n-k1,1)) * Z1tZ1_inv @ meat1 @ Z1tZ1_inv
        f_stat = (b_fs[0] / np.sqrt(V1[0, 0])) ** 2
    except np.linalg.LinAlgError:
        return None

    # --- Stage 2: tot_hat + year dummies + overseas_share_contemp +
    # region dummies (fixed effects) + constant ---
    yr_dummies = pd.get_dummies(est['year'], prefix='yr',
                                 drop_first=True).astype(float)
    yr_cols = yr_dummies.columns.tolist()
    for c in yr_cols:
        est[c] = yr_dummies[c].values

    region_dummies = pd.get_dummies(est['region'], prefix='rg',
                                     drop_first=True).astype(float)
    rg_cols = region_dummies.columns.tolist()
    for c in rg_cols:
        est[c] = region_dummies[c].values

    y = est[outcome].values.astype(float)
    C = np.column_stack(
        [est['overseas_share_contemp'].values] +
        [est[c].values for c in yr_cols] +
        [est[c].values for c in rg_cols] +
        [np.ones(n)]
    )
    X_ss = np.column_stack([tot_hat.reshape(-1, 1), C])
    k = X_ss.shape[1]

    try:
        b_ss, _, _, _ = np.linalg.lstsq(X_ss, y, rcond=None)
        resid = y - X_ss @ b_ss
        meat = np.zeros((k, k))
        for c in unique_c:
            m = clusters == c
            s = X_ss[m].T @ resid[m]
            meat += np.outer(s, s)
        XtX_inv = np.linalg.inv(X_ss.T @ X_ss)
        V = (G/max(G-1,1)) * ((n-1)/max(n-k,1)) * XtX_inv @ meat @ XtX_inv
        se = np.sqrt(V[0, 0])
        coef = b_ss[0]
        t = coef / se
        pval = 2 * (1 - stats.t.cdf(abs(t), df=max(G-1, 1)))
    except np.linalg.LinAlgError:
        return None

    return dict(coef=coef, se=se, pval=pval, f_stat=f_stat, n=n)


def regional_mechanism(df, paye):
    """
    Regional test, per explicitly agreed design: ONE first stage
    (bartik_region alone, mean-of-LA-bartik), with region fixed effects
    and PAYE overseas_share both in the second stage.

    Stage 1: tot ~ bartik_region + constant ONLY.
    Stage 2: outcome ~ tot_hat + year dummies + overseas_share_contemp
    (PAYE, CONTEMPORANEOUS -- year-by-year, not a fixed 2016 baseline)
    + region fixed effects (9 region dummies).

    Switched from a fixed 2016 baseline to contemporaneous values on
    explicit request: 2016 predates the entire relevant visa-policy
    history (Health & Care Worker visa route launched Aug 2020; social
    care added to the Shortage Occupation List Feb 2022), so a fixed
    pre-period snapshot can't represent a mechanism -- overseas
    recruitment as a "pressure relief valve" for care staff lost to
    retail -- that is itself time-varying due to policy change within
    the analysis window. Known, accepted tradeoff: contemporaneous
    overseas_share may be partly a mediator (if overseas recruitment
    responds within-year to retail-driven staff loss), which could
    absorb some of the very effect being estimated. Kept as a plain
    additive control (not interacted, not used to split the sample) to
    limit that risk as far as possible. Deliberately confined to this
    regional analysis only -- the LA-level Section 3 panel is NOT
    touched, per explicit decision to avoid destabilizing results that
    have already been reviewed and presented.
    """
    print("\n" + "=" * 70)
    print("SECTION 4: REGIONAL -- SINGLE FIRST STAGE, REGION FE + PAYE (STAGE 2)")
    print("=" * 70)

    eng = df[~df['region'].isin(['Scotland', 'Wales', 'Northern Ireland'])].copy()

    # Stage-1 instrument: region-year MEAN of the already-computed
    # LA-level bartik instrument (simple average, not a fresh
    # region-level reconstruction).
    bartik_r = eng.groupby(['region', 'year'])['bartik'].mean().reset_index()
    bartik_r = bartik_r.rename(columns={'bartik': 'bartik_region'})
    retail_r = eng.groupby(['region', 'year'])['tot'].mean().reset_index()
    retail_r = retail_r.merge(bartik_r, on=['region', 'year'], how='left')

    # --- Collapse outcomes to region-year (analysis window only) ---
    analysis = eng[eng['year'].between(YEAR_MIN_ANALYSIS, YEAR_MAX_ANALYSIS)].copy()
    regional = analysis.groupby(['region', 'year']).agg(
        pop_total          = ('pop_total',          'sum'),
        vacant_posts       = ('vacant_posts',       'sum'),
        filled_posts       = ('filled_posts',       'sum'),
        claimants_december = ('claimants_december', 'sum'),
        claimants_annual   = ('claimants_annual',   'sum'),
    ).reset_index()

    regional['posts'] = (regional['filled_posts'].fillna(0) +
                         regional['vacant_posts'].fillna(0))
    regional['vacancy_rate'] = np.where(
        regional['posts'] > 0, (regional['vacant_posts'] / regional['posts']) * 100,
        np.nan)
    regional['benefit_rate']        = (regional['claimants_december'] /
                                        regional['pop_total'] * 1000)
    regional['benefit_rate_annual'] = (regional['claimants_annual'] /
                                        regional['pop_total'] * 1000)

    regional = regional.merge(
        retail_r[['region', 'year', 'tot', 'bartik_region']],
        on=['region', 'year'], how='left')

    # PAYE overseas share, CONTEMPORANEOUS (year-by-year, not the
    # earlier fixed 2016 baseline). Explicit decision: 2016 predates the
    # entire relevant visa-policy history (Health & Care Worker route
    # launched Aug 2020; care added to Shortage Occupation List Feb
    # 2022), so a fixed pre-period snapshot can't represent a mechanism
    # that is itself time-varying due to policy change within the
    # analysis window. Known risk, accepted rather than ignored: if
    # overseas recruitment responds within-year to retail-driven care
    # staff loss, this control is partly a mediator and could absorb
    # some of the very effect being estimated -- kept as a plain
    # additive control (not interacted, not used to split the sample)
    # to limit that risk as far as possible, in the same spirit as the
    # already-accepted small-N caveats on this section. Deliberately
    # NOT applied to the LA-level Section 3 panel, which stays
    # untouched -- this is confined to the regional analysis only.
    paye_eng = paye[paye['region_code'].str.startswith('E12')].copy()
    overseas_contemp = paye_eng[
        ['region', 'year', 'overseas_share']
    ].rename(columns={'overseas_share': 'overseas_share_contemp'})
    regional = regional.merge(overseas_contemp, on=['region', 'year'], how='left')

    print(f"\n  N regions: {regional['region'].nunique()}")
    print(f"  N obs:     {len(regional)}")
    print("  Stage 1 (single, shared): tot ~ bartik_region + constant")
    print("  Stage 2: outcome ~ tot_hat + year FE + overseas_share")
    print("  (CONTEMPORANEOUS, year-by-year -- not 2016 baseline) +")
    print("  region FE. Clustered SEs by region.")
    print("  CAUTION: contemporaneous overseas_share may be partly a")
    print("  mediator, not purely a predetermined control -- accepted")
    print("  tradeoff, see docstring.")
    print()

    outcomes = [
        ('vacant_posts',        'Vacant posts (social care)'),
        ('vacancy_rate',        'Vacancy rate (social care)'),
        ('benefit_rate',        'Benefit rate (Dec)'),
        ('benefit_rate_annual', 'Benefit rate (annual)'),
    ]

    for outcome, label in outcomes:
        if outcome not in regional.columns:
            continue
        r = run_iv_region_fe_stage2(regional, outcome)
        if r is None:
            print(f"  {label}: could not estimate (insufficient data)")
            continue
        sig = '***' if r['pval'] < 0.01 else '**' if r['pval'] < 0.05 \
            else '*' if r['pval'] < 0.10 else '(ns)'
        print(f"  {label}: beta={r['coef']:>10.3f} (SE={r['se']:.3f}, "
              f"p={r['pval']:.3f}) {sig}  F(stage1)={r['f_stat']:.2f}  "
              f"N={r['n']}")

    print()
    print("  NOTE: N=9 regions -- stage 2 has more parameters than")
    print("  clusters (region FE + year FE + PAYE + tot_hat). Treat as a")
    print("  scoping exercise, not a reliable causal estimate.")

def raw_figures_check(df):
    """
    Compare raw panel figures directly against Rama's .dta file.
    Checks retailer counts and benefit claimants for matched LAs.
    Flags worrying discrepancies from postcode vs polygon assignment.
    """
    print("\n" + "=" * 70)
    print("RAW FIGURES COMPARISON vs RAMA'S PANEL")
    print("=" * 70)

    rama_path = os.path.join('data', 'rama.dta')
    if not os.path.exists(rama_path):
        print(f"  Rama's panel not found at {rama_path} -- skipping")
        return

    rama = pd.read_stata(rama_path)
    rama['la_name_lower'] = rama['local_auth'].str.strip().str.lower()
    df['la_name_lower']   = df['la_name'].str.strip().str.lower()

    for year in [2020, 2021, 2022, 2023]:
        ours = df[df['year'] == year].copy()
        r    = rama[rama['year'] == year].copy()

        merged = ours.merge(
            r[['la_name_lower', 'retailers', 'retailers_new',
               'benefit_claimants', 'pop_all']].rename(
                   columns={'benefit_claimants': 'rama_claimants',
                            'pop_all': 'rama_pop'}),
            on='la_name_lower', how='inner'
        )
        n = len(merged)

        # Retailer differences
        merged['diff_tot'] = merged['tot']     - merged['retailers']
        merged['diff_new'] = merged['tot_new'] - merged['retailers_new']

        # Claimant differences
        merged['diff_cc']     = merged['claimants_december'] - merged['rama_claimants']
        merged['diff_cc_pct'] = (merged['diff_cc'] / merged['rama_claimants'] * 100)

        print(f"\n  Year {year} ({n} matched LAs):")
        print(f"    Retailers (total):  mean diff={merged['diff_tot'].mean():+.1f}, "
              f"SD={merged['diff_tot'].std():.1f}, "
              f"max={merged['diff_tot'].abs().max():.0f}")
        print(f"    Retailers (disc):   mean diff={merged['diff_new'].mean():+.2f}, "
              f"SD={merged['diff_new'].std():.2f}")
        print(f"    Claimants:          mean diff={merged['diff_cc'].mean():+.0f}, "
              f"mean %diff={merged['diff_cc_pct'].mean():+.1f}%")

        # Show which LAs failed to name-match this year (present in our panel,
        # not found in Rama's file by la_name_lower). Helps confirm whether
        # the 148-vs-145 gap is just the combined-split naming issue
        # (NORTHANTS_COMBINED etc.) or something else worth investigating.
        unmatched = ours[~ours['la_name_lower'].isin(r['la_name_lower'])]
        if len(unmatched) > 0:
            print(f"    Unmatched LAs ({len(unmatched)}): "
                  f"{', '.join(unmatched['la_name_lower'].tolist())}")

        # Flag large retailer discrepancies
        large = merged[merged['diff_tot'].abs() > 5]
        if len(large) > 0:
            print(f"    LAs with >5 retailer difference ({len(large)}):")
            for _, row in large.nlargest(5, 'diff_tot').iterrows():
                print(f"      {row['la_name_lower']:<35} "
                      f"ours={row['tot']:.0f} rama={row['retailers']:.0f} "
                      f"diff={row['diff_tot']:+.0f}")

    # Overall correlation check
    ours_2020  = df[df['year'] == 2020].copy()
    rama_2020  = rama[rama['year'] == 2020].copy()
    merged_all = ours_2020.merge(
        rama_2020[['la_name_lower', 'retailers', 'retailers_new']],
        on='la_name_lower', how='inner'
    )
    corr_tot = merged_all[['tot', 'retailers']].corr().iloc[0,1]
    corr_new = merged_all[['tot_new', 'retailers_new']].corr().iloc[0,1]
    print(f"\n  Correlation our vs Rama retailers (2020):")
    print(f"    Total retailers:  r={corr_tot:.3f}")
    print(f"    Discounters only: r={corr_new:.3f}")
    print()
    if corr_tot > 0.97:
        print("  Retailer counts: CONSISTENT (r>0.97) -- spatial join acceptable")
    elif corr_tot > 0.90:
        print("  Retailer counts: BROADLY CONSISTENT (r>0.90) -- minor boundary effects")
    else:
        print("  Retailer counts: CONCERNING (r<0.90) -- investigate postcode vs polygon")


# ---------------------------------------------------------------------------
# Section 6: Summary comparison to paper
# ---------------------------------------------------------------------------

def summary_vs_paper(f_stat, main_results, df):
    """Print comparison table vs paper benchmarks."""
    print("\n" + "=" * 70)
    print("SUMMARY: OUR PANEL vs PAPER BENCHMARKS")
    print("=" * 70)

    # Computed live from the current panel -- previously hardcoded as "153",
    # which was stale text left over from an earlier panel version and did
    # not reflect the actual data being validated in this run.
    n_las = df['la_code'].nunique()

    print(f"\n  {'Metric':<35} {'Our panel':>15} {'Paper':>15}")
    print("  " + "-" * 65)

    # First stage F
    paper_f = 43.11
    flag = 'OK' if abs(f_stat - paper_f) / paper_f < 0.3 else '<- check'
    print(f"  {'First-stage F':35} {f_stat:>15.2f} {paper_f:>15.2f}  {flag}")

    # Main outcomes
    benchmarks = {
        'vacant_posts':  (1.85,   0.885, 'Expect null'),
        'vacancy_rate':  (0.164,  0.254, 'Expect null'),
        'employees':     (-4.77,  0.850, 'Expect null'),
        'benefit_rate':  (-0.495, 0.040, 'Expect NEGATIVE *'),
    }

    for outcome, (paper_coef, paper_p, note) in benchmarks.items():
        if outcome in main_results:
            r = main_results[outcome]
            sig_ours  = '*' if r.pval < 0.10 else ''
            sig_paper = '*' if paper_p < 0.10 else ''
            flag = 'OK' if (r.pval < 0.10) == (paper_p < 0.10) else '<- check'
            print(f"  {note:<35} beta={r.coef:>6.3f} p={r.pval:.3f}{sig_ours:<2}"
                  f"  beta={paper_coef:>6.3f} p={paper_p:.3f}{sig_paper:<2}  {flag}")

    print()
    print("  Notes:")
    print("  - We use pop_65plus; paper uses pop_60 (minor difference expected)")
    print(f"  - We have {n_las} upper-tier LAs; paper has 150")
    print("  - Retail counts ~20% higher (same national total, fewer larger units)")
    print("  - See RETAIL_METHODOLOGY_NOTE.md for full explanation")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("BARTIK IV SANITY CHECK")
    print("Replicating Radakrishnan et al. (2025) using Python pipeline")
    print("=" * 70)

    if not os.path.exists(SFC_FILE):
        print(f"\nERROR: {SFC_FILE} not found")
        print("Run: python make.py england-sfc")
        return

    print("\nLoading data...")
    df   = load_data()
    paye = load_paye_regional()

    df   = construct_bartik(df)
    f_stat, fs_coef = first_stage(df)
    raw_figures_check(df)
    main_results     = main_iv(df)
    regional_mechanism(df, paye)
    summary_vs_paper(f_stat, main_results, df)

    print(f"\n{'=' * 70}")
    print("DONE")
    print(f"{'=' * 70}")
    print("\nIf F-statistic is in range 20-60 and benefit_rate is the only")
    print("significant outcome (negative), the pipeline is validated.")
    print("Hand off to Rama for full Stata analysis.")


if __name__ == '__main__':
    main()
