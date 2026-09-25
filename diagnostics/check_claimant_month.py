"""
check_claimant_month.py - Find which month of claimant count matches Rama's annual figure.
"""
import pandas as pd
import os

# Load monthly claimant data - need to re-download or check if we have it
# For now check what our annual means look like vs Rama for key LAs
r = pd.read_stata('data/rama.dta')

# Check if we have monthly data cached
monthly_path = 'data/intermediate/claimant_count_monthly.csv'
if not os.path.exists(monthly_path):
    print("Monthly data not cached. Downloading from Nomis for Birmingham only...")
    import requests
    # Fetch monthly for Birmingham (E08000025) 2020
    url = (
        "https://www.nomisweb.co.uk/api/v01/dataset/NM_162_1/data.csv"
        "?geography=E08000025"
        "&date=2020-01,2020-02,2020-03,2020-04,2020-05,2020-06,"
        "2020-07,2020-08,2020-09,2020-10,2020-11,2020-12"
        "&gender=0&age=0&measure=1&measures=20100"
        "&select=date_name,geography_code,obs_value"
        "&uid=0xnomisanon"
    )
    resp = requests.get(url, timeout=30)
    monthly = pd.read_csv(pd.io.common.StringIO(resp.text))
    monthly.columns = monthly.columns.str.lower()
    monthly = monthly.rename(columns={
        'geography_code': 'la_code',
        'obs_value': 'claimants',
        'date_name': 'month'
    })
    print(monthly.to_string())
    print()

    # Rama's Birmingham 2020
    brum_rama = r[(r['local_auth']=='Birmingham') & (r['year']==2020)]['benefit_claimants'].iloc[0]
    print(f"Rama Birmingham 2020: {brum_rama:,.0f}")
    print(f"Our annual mean:      {monthly['claimants'].mean():,.0f}")
    print()
    print("Monthly values:")
    for _, row in monthly.iterrows():
        match = ' <-- MATCH' if abs(row['claimants'] - brum_rama) < 500 else ''
        print(f"  {row['month']}: {row['claimants']:,.0f}{match}")

else:
    print(f"Monthly data exists at {monthly_path}")
    df = pd.read_csv(monthly_path)
    print(df.head())
