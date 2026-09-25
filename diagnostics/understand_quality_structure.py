"""Understand the ONS quality indicator structure"""
import pandas as pd

df = pd.read_csv('data/wellbeing_la.csv')

# Get one LA-year-measure with all its rows
# Filter to a known LA
leeds_rows = df[df['administrative-geography'] == 'E08000035']

if len(leeds_rows) > 0:
    # Get one specific year-measure
    sample = leeds_rows[(leeds_rows['yyyy-yy'] == '2019-20')]
    
    if len(sample) > 0:
        # Get life satisfaction
        ls_sample = sample[sample['measure-of-wellbeing'].str.contains('satisfaction', case=False, na=False)]
        
        print("Leeds 2019-20 Life Satisfaction - ALL ROWS:")
        print("=" * 70)
        print(ls_sample[['Estimate', 'v4_3', 'Lower limit', 'Upper limit']])
        
        print("\n" + "=" * 70)
        print("INTERPRETATION")
        print("=" * 70)
        
        # Check if all 5 rows have same CI or different
        if len(ls_sample) >= 5:
            unique_means = ls_sample['v4_3'].nunique()
            unique_lower = ls_sample['Lower limit'].nunique()
            unique_upper = ls_sample['Upper limit'].nunique()
            
            print(f"Unique mean values: {unique_means}")
            print(f"Unique lower bounds: {unique_lower}")
            print(f"Unique upper bounds: {unique_upper}")
            
            if unique_means == 1 and unique_lower == 1 and unique_upper == 1:
                print("\n✓ All 5 quality rows have SAME mean and CI")
                print("  → Quality flag is metadata, CI already captures precision")
                print("  → Use CI-derived SE for weighting, ignore quality flag")
            else:
                print("\n✗ Different rows have DIFFERENT values")
                print("  → Quality rows might represent different estimators")
                print("  → Need to understand what each row means")
        else:
            print(f"Only {len(ls_sample)} rows found (expected 5)")
    else:
        print("No 2019-20 data for Leeds")
else:
    print("Leeds not found - trying different LA...")
    # Try any LA
    any_la = df['administrative-geography'].iloc[0]
    print(f"Using {any_la} instead...")
    
# Just show first 20 rows of ANYTHING to understand structure
print("\n" + "=" * 70)
print("First 20 rows of CSV (to see structure):")
print("=" * 70)
cols = ['administrative-geography', 'yyyy-yy', 'measure-of-wellbeing', 
        'Estimate', 'v4_3', 'Lower limit', 'Upper limit']
print(df[cols].head(20))
