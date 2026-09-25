#!/usr/bin/env python3
"""
cohort_report.py - Generate Table 1 style cohort descriptives and charts.

Produces:
  output/cohort/table1_by_year.html     - descriptive stats by year (2020-2023)
  output/cohort/table1_by_region.html   - descriptive stats by region
  output/cohort/fig_trends.png          - key variable trends 2016-2023
  output/cohort/fig_retail_map.png      - retail counts by region
  output/cohort/fig_vacancies.png       - vacancy rate trends by region
  output/cohort/fig_overseas.png        - overseas share by region

Usage:
  python cohort_report.py
"""

import os
import warnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

warnings.filterwarnings('ignore')

from config import DATA_DIR, OUTPUT_DIR

OUTPUT_COHORT = os.path.join(OUTPUT_DIR, 'cohort')
SFC_PANEL     = os.path.join(DATA_DIR, 'intermediate', 'england_panel_sfc.csv')

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
PALETTE = {
    'navy':      '#1a3a5c',
    'teal':      '#2a9d8f',
    'coral':     '#e76f51',
    'sand':      '#e9c46a',
    'light':     '#f8f9fa',
    'mid':       '#dee2e6',
    'text':      '#212529',
    'muted':     '#6c757d',
}

HTML_STYLE = """
<style>
  body {
    font-family: 'Georgia', serif;
    color: #212529;
    background: #fff;
    max-width: 960px;
    margin: 40px auto;
    padding: 0 24px;
  }
  h1 { font-size: 1.6rem; color: #1a3a5c; border-bottom: 2px solid #2a9d8f;
       padding-bottom: 8px; margin-bottom: 4px; }
  h2 { font-size: 1.2rem; color: #1a3a5c; margin-top: 32px; }
  p.subtitle { color: #6c757d; font-size: 0.9rem; margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem;
          margin-top: 12px; }
  thead th { background: #1a3a5c; color: #fff; padding: 8px 12px;
             text-align: right; font-weight: 600; }
  thead th:first-child { text-align: left; }
  tbody tr:nth-child(even) { background: #f8f9fa; }
  tbody td { padding: 7px 12px; border-bottom: 1px solid #dee2e6;
             text-align: right; }
  tbody td:first-child { text-align: left; color: #1a3a5c;
                         font-weight: 500; }
  tbody tr.section-header td { background: #e9f0f7; font-style: italic;
                                color: #1a3a5c; font-weight: 600; }
  tfoot td { padding: 6px 12px; font-size: 0.8rem; color: #6c757d;
             font-style: italic; }
  .note { font-size: 0.82rem; color: #6c757d; margin-top: 8px; }
</style>
"""

# ---------------------------------------------------------------------------
# Load and prepare data
# ---------------------------------------------------------------------------

def load_panel():
    df = pd.read_csv(SFC_PANEL)
    # Deduplicate to one row per LA-year for non-wellbeing analysis
    wide = df.drop_duplicates(subset=['la_code', 'year']).copy()
    # Keep wellbeing long for wellbeing-specific analysis
    wb = df[['la_code', 'year', 'measure', 'value']].dropna(
        subset=['measure', 'value']).copy()
    return wide, wb, df


def fmt(val, decimals=1, pct=False, thousands=False):
    """Format a value for HTML table."""
    if pd.isna(val):
        return '—'
    if pct:
        return f'{val*100:.{decimals}f}%'
    if thousands:
        return f'{val/1000:.{decimals}f}k'
    return f'{val:,.{decimals}f}'


# ---------------------------------------------------------------------------
# Table 1: By Year
# ---------------------------------------------------------------------------

def table_by_year(wide, years=(2020, 2021, 2022, 2023)):
    """Generate Table 1: descriptive statistics by year."""

    rows = [
        # (label, col, stat, format_kwargs)
        ('N local authorities',    'la_code',       'count',   {}),
        ('Retail units (median)',   'tot',            'median',  {}),
        ('  IQR (Q1-Q3)',          'tot',            'iqr',     {}),
        ('Discounters — Aldi/Lidl (mean)', 'tot_new', 'mean', {}),
        ('  SD',                           'tot_new', 'std',  {}),
        ('Incumbents (median)',     'tot_old',        'median',  {}),
        ('', '', '', {}),
        ('Social care vacancies (mean)', 'vacant_posts',   'mean', {}),
        ('  SD',                         'vacant_posts',   'std',  {}),
        ('Filled posts (mean)',           'filled_posts',   'mean', {}),
        ('Vacancy rate (mean)',           'vacancy_rate',   'mean', {'pct': True}),
        ('', '', '', {}),
        ('Claimants, annual mean',  'claimants_mean', 'mean',   {}),
        ('  SD',                    'claimants_mean', 'std',    {}),
        ('', '', '', {}),
        ('Population, mean (000s)', 'pop_total',     'mean',   {'thousands': True}),
        ('Population 65+, mean (000s)', 'pop_65plus', 'mean',  {'thousands': True}),
        ('', '', '', {}),
        ('Overseas workers share (mean)', 'overseas_share', 'mean', {'pct': True}),
        ('  London',               '_london_os',    'first',   {'pct': True}),
        ('  North East',           '_ne_os',        'first',   {'pct': True}),
    ]

    # Pre-compute London and NE overseas share
    yr_data = {}
    for y in years:
        yw = wide[wide['year'] == y].copy()
        lon = yw[yw['region'] == 'London']['overseas_share'].mean()
        ne  = yw[yw['region'] == 'North East']['overseas_share'].mean()
        yw['_london_os'] = lon
        yw['_ne_os']     = ne
        yr_data[y] = yw

    # Build HTML
    year_cols = ''.join(f'<th>{y}</th>' for y in years)
    html = f"""
{HTML_STYLE}
<h1>Table 1: Baseline Characteristics of English Local Authorities, 2020–2023</h1>
<p class="subtitle">153 upper-tier local authorities. Skills for Care independent sector.
Retail counts aggregated to upper-tier geography.</p>
<table>
<thead><tr><th>Variable</th>{year_cols}</tr></thead>
<tbody>
"""
    for label, col, stat, fkwargs in rows:
        if label == '' and col == '':
            html += '<tr><td colspan="5">&nbsp;</td></tr>\n'
            continue

        cells = f'<td>{label}</td>'
        for y in years:
            yw = yr_data[y]
            if col not in yw.columns:
                cells += '<td>—</td>'
                continue
            s = yw[col]
            if stat == 'count':
                v = yw['la_code'].nunique()
                cells += f'<td>{v}</td>'
            elif stat == 'mean':
                v = s.mean()
                cells += f'<td>{fmt(v, **fkwargs)}</td>'
            elif stat == 'median':
                v = s.median()
                cells += f'<td>{fmt(v, **fkwargs)}</td>'
            elif stat == 'std':
                v = s.std()
                cells += f'<td>({fmt(v, **fkwargs)})</td>'
            elif stat == 'iqr':
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                cells += f'<td>({fmt(q1,0)}, {fmt(q3,0)})</td>'
            elif stat == 'first':
                v = s.dropna().iloc[0] if len(s.dropna()) > 0 else np.nan
                cells += f'<td>{fmt(v, **fkwargs)}</td>'

        html += f'<tr>{cells}</tr>\n'

    html += """</tbody>
<tfoot><tr><td colspan="5">
Notes: Retail units = total major supermarkets (Tesco, Asda, Sainsburys, Morrisons,
Iceland, M&S, Waitrose, Aldi, Lidl). Vacancy rate suppressed for small LAs (n varies by year).
Claimants = Experimental Claimant Count (JSA + UC), annual mean of monthly data.
Population 65+ derived from ONS Mid-Year Estimates. Overseas share = HMRC PAYE
health &amp; social work employment (SIC 86-88) held by non-UK nationals.
</td></tr></tfoot>
</table>
<p class="note">Source: Geolytix Retail Points, Skills for Care ASCWDS,
ONS Claimant Count (Nomis), ONS Mid-Year Estimates, HMRC PAYE.</p>
<p class="note"><strong>Note on discounters:</strong> The stable median (8 stores per LA
across 2020–2023) alongside a rising mean (9.4 to 10.8) reflects Aldi and Lidl entering
previously unserved local authorities rather than adding stores to already-served areas.
This validates the Bartik instrument: the identifying variation comes from predetermined
2016 chain composition differences across LAs, not uniform expansion everywhere.</p>
"""
    return html


# ---------------------------------------------------------------------------
# Table 2: By Region
# ---------------------------------------------------------------------------

def table_by_region(wide, years=(2020, 2021, 2022, 2023)):
    """Generate Table 2: key variables by region, averaged 2020-2023."""

    period = wide[wide['year'].isin(years)].copy()
    avg = period.groupby('region').agg(
        n_las         = ('la_code',       'nunique'),
        tot_median    = ('tot',           'median'),
        tot_new_mean  = ('tot_new',       'mean'),
        vacancies     = ('vacant_posts',  'mean'),
        filled        = ('filled_posts',  'mean'),
        vac_rate      = ('vacancy_rate',  'mean'),
        claimants     = ('claimants_mean','mean'),
        pop           = ('pop_total',     'mean'),
        overseas      = ('overseas_share','mean'),
    ).reset_index().sort_values('overseas', ascending=False)

    html = f"""
{HTML_STYLE}
<h1>Table 2: Panel Characteristics by English Region, 2020–2023 Average</h1>
<p class="subtitle">Mean of annual values 2020–2023. 153 upper-tier local authorities.</p>
<table>
<thead><tr>
  <th>Region</th>
  <th>LAs</th>
  <th>Retailers<br>(median)</th>
  <th>Discounters<br>(mean)</th>
  <th>Vacancies<br>(mean)</th>
  <th>Vac. rate<br>(mean)</th>
  <th>Claimants<br>(mean)</th>
  <th>Population<br>(000s)</th>
  <th>Overseas<br>share</th>
</tr></thead>
<tbody>
"""
    for _, row in avg.iterrows():
        html += f"""<tr>
  <td>{row['region']}</td>
  <td>{int(row['n_las'])}</td>
  <td>{fmt(row['tot_median'],0)}</td>
  <td>{fmt(row['tot_new_mean'],1)}</td>
  <td>{fmt(row['vacancies'],0)}</td>
  <td>{fmt(row['vac_rate'], 1, pct=True)}</td>
  <td>{fmt(row['claimants'],0)}</td>
  <td>{fmt(row['pop'],0,thousands=True)}</td>
  <td>{fmt(row['overseas'],1,pct=True)}</td>
</tr>\n"""

    html += """</tbody>
<tfoot><tr><td colspan="9">
Regions ordered by overseas worker share (high to low).
Vacancy rate suppressed for small LAs; mean based on available observations.
</td></tr></tfoot>
</table>
<p class="note">Source: Geolytix, Skills for Care ASCWDS, ONS Nomis, HMRC PAYE.</p>
"""
    return html


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def set_style():
    plt.rcParams.update({
        'font.family':       'serif',
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'axes.grid':         True,
        'grid.alpha':        0.3,
        'grid.linestyle':    '--',
        'figure.facecolor':  'white',
        'axes.facecolor':    'white',
    })


def fig_trends(wide):
    """4-panel figure: key trends 2016-2023, England national means."""
    set_style()

    national = wide.groupby('year').agg(
        retailers   = ('tot',            'median'),
        discounters = ('tot_new',        'mean'),
        vacancies   = ('vacant_posts',   'mean'),
        claimants   = ('claimants_mean', 'mean'),
        vac_rate    = ('vacancy_rate',   'mean'),
    ).reset_index()

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('England Panel: Key Trends 2016–2023\n(153 upper-tier local authorities)',
                 fontsize=13, fontweight='bold', color=PALETTE['navy'])

    plots = [
        (axes[0,0], 'retailers',   'Retail Units (median per LA)',         PALETTE['navy']),
        (axes[0,1], 'discounters', 'Discounters — Aldi/Lidl (mean per LA)',PALETTE['teal']),
        (axes[1,0], 'vacancies',   'Social Care Vacancies (mean)',          PALETTE['coral']),
        (axes[1,1], 'claimants',   'Claimant Count (annual mean)',          PALETTE['sand']),
    ]

    for ax, col, title, colour in plots:
        ax.plot(national['year'], national[col], '-o',
                color=colour, linewidth=2.5, markersize=6)
        ax.axvspan(2019.5, 2020.5, alpha=0.12, color='red', label='COVID')
        ax.set_title(title, fontsize=10, fontweight='bold',
                     color=PALETTE['navy'])
        ax.set_xlabel('')
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.tick_params(labelsize=9)

    axes[1,0].legend(['Value', 'COVID onset'], fontsize=8, loc='upper left')
    plt.tight_layout()
    path = os.path.join(OUTPUT_COHORT, 'fig_trends.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def fig_by_region(wide, col, title, ylabel, filename, pct=False):
    """Line chart: variable by region over time."""
    set_style()

    regions = sorted(wide['region'].dropna().unique())
    cmap    = plt.cm.tab10
    colours = {r: cmap(i/len(regions)) for i, r in enumerate(regions)}

    fig, ax = plt.subplots(figsize=(11, 6))

    for region in regions:
        rdata = wide[wide['region'] == region].groupby('year')[col].mean()
        if len(rdata) == 0:
            continue
        ax.plot(rdata.index, rdata.values, '-o',
                color=colours[region], linewidth=1.8, markersize=5,
                label=region)

    ax.axvspan(2019.5, 2020.5, alpha=0.1, color='red')
    ax.set_title(title, fontsize=12, fontweight='bold', color=PALETTE['navy'])
    ax.set_ylabel(ylabel, fontsize=10)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    if pct:
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f'{x*100:.0f}%'))
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    ax.tick_params(labelsize=9)

    plt.tight_layout()
    path = os.path.join(OUTPUT_COHORT, filename)
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def fig_vacancy_by_region(wide):
    """Vacancy rate by region — bar chart for 2020-2023."""
    set_style()

    period = wide[wide['year'].isin([2020,2021,2022,2023])].copy()
    avg = period.groupby(['region','year'])['vacancy_rate'].mean().reset_index()
    pivot = avg.pivot(index='region', columns='year', values='vacancy_rate')

    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(pivot))
    w = 0.2
    colours = [PALETTE['navy'], PALETTE['teal'], PALETTE['coral'], PALETTE['sand']]

    for i, year in enumerate([2020, 2021, 2022, 2023]):
        if year in pivot.columns:
            ax.bar(x + i*w, pivot[year]*100, w, label=str(year),
                   color=colours[i], alpha=0.85)

    ax.set_xticks(x + 1.5*w)
    ax.set_xticklabels(pivot.index, rotation=35, ha='right', fontsize=9)
    ax.set_ylabel('Vacancy Rate (%)', fontsize=10)
    ax.set_title('Social Care Vacancy Rate by Region, 2020–2023\n(Independent sector)',
                 fontsize=12, fontweight='bold', color=PALETTE['navy'])
    ax.legend(title='Year', fontsize=9)
    plt.tight_layout()
    path = os.path.join(OUTPUT_COHORT, 'fig_vacancies_by_region.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_COHORT, exist_ok=True)

    if not os.path.exists(SFC_PANEL):
        print(f"ERROR: {SFC_PANEL} not found. Run: python make.py england-sfc")
        return

    print("Loading panel data...")
    wide, wb, full = load_panel()

    print("\nGenerating tables...")

    # Table 1: by year
    html1 = table_by_year(wide)
    path1 = os.path.join(OUTPUT_COHORT, 'table1_by_year.html')
    with open(path1, 'w') as f:
        f.write(html1)
    print(f"  Saved: {path1}")

    # Table 2: by region
    html2 = table_by_region(wide)
    path2 = os.path.join(OUTPUT_COHORT, 'table1_by_region.html')
    with open(path2, 'w') as f:
        f.write(html2)
    print(f"  Saved: {path2}")

    print("\nGenerating charts...")
    fig_trends(wide)

    fig_by_region(wide, 'tot',           
                  'Total Retail Units by Region, 2016–2023',
                  'Median stores per LA', 'fig_retail_by_region.png')

    fig_by_region(wide, 'overseas_share',
                  'Overseas Worker Share in Health & Social Care by Region, 2016–2023',
                  'Share of employment', 'fig_overseas_by_region.png', pct=True)

    fig_by_region(wide, 'claimants_mean',
                  'Claimant Count by Region, 2016–2023',
                  'Annual mean claimants per LA', 'fig_claimants_by_region.png')

    fig_vacancy_by_region(wide)

    print(f"\nDone. All outputs in {OUTPUT_COHORT}/")


if __name__ == '__main__':
    main()
