"""Check what estimate types exist for Northamptonshire"""
import pandas as pd

df = pd.read_csv('data/wellbeing_la.csv')

# Get Northamptonshire data
northants = df[df['administrative-geography'].isin(['E06000061', 'E06000062'])]

print(f"Total Northamptonshire rows: {len(northants)}")

# Find estimate column
est_cols = [c for c in df.columns if 'estimate' in c.lower()]
print(f"\nEstimate columns: {est_cols}")

if est_cols:
    est_col = est_cols[0]
    print(f"\nUsing column: {est_col}")
    print(f"\nUnique estimate types in Northamptonshire data:")
    print(northants[est_col].value_counts())
    
    # Check by year
    print(f"\nEstimate types by year (life-satisfaction):")
    northants_ls = northants[northants['measure-of-wellbeing'].str.contains('life', case=False, na=False)]
    
    for year in sorted(northants_ls['yyyy-yy'].unique()):
        year_data = northants_ls[northants_ls['yyyy-yy'] == year]
        estimates = year_data[est_col].value_counts().to_dict()
        print(f"  {year}: {estimates}")

else:
    print("No estimate column found!")

# Check what the current filter is doing
print("\n" + "=" * 70)
print("WHAT GETS FILTERED OUT?")
print("=" * 70)

if est_cols:
    est_col = est_cols[0]
    
    # Current filter
    mean_only = northants[northants[est_col].str.contains('mean|average', case=False, na=False)]
    print(f"With 'mean|average' filter: {len(mean_only)} rows")
    
    # All estimates
    print(f"Without filter: {len(northants)} rows")
    print(f"Difference: {len(northants) - len(mean_only)} rows excluded")
    
    # What's excluded
    excluded = northants[~northants[est_col].str.contains('mean|average', case=False, na=False)]
    print(f"\nExcluded estimate types:")
    print(excluded[est_col].value_counts())
