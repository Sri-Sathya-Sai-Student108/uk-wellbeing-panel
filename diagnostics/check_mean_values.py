"""Check actual values in average-mean estimate rows for Northamptonshire"""
import pandas as pd

df = pd.read_csv('data/wellbeing_la.csv')

# Filter to just average-mean estimates for Northamptonshire
northants = df[df['administrative-geography'].isin(['E06000061', 'E06000062'])]
northants_mean = northants[northants['wellbeing-estimate'] == 'average-mean']

print("NORTHAMPTONSHIRE average-mean ESTIMATES")
print("=" * 70)
print(f"Total rows: {len(northants_mean)}")

# Get life satisfaction for E06000061
north_ls = northants_mean[(northants_mean['administrative-geography'] == 'E06000061') & 
                          (northants_mean['measure-of-wellbeing'].str.contains('life', case=False, na=False))]

print("\nE06000061 (North) - Life Satisfaction average-mean:")
# Find the value column
value_cols = [c for c in df.columns if c in ['v4_1', 'v4_3', 'v4_0', 'observation', 'value']]
if value_cols:
    value_col = value_cols[0]
    print(f"Value column: {value_col}")
    print(north_ls[['yyyy-yy', value_col]].sort_values('yyyy-yy'))
else:
    print("Can't find value column!")
    print(f"Columns: {list(df.columns[:15])}")
