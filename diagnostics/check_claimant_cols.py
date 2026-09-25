"""check_claimant_cols.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
df = pd.read_csv('data/intermediate/claimant_count_annual.csv')
print('Columns:', df.columns.tolist())
print('Shape:', df.shape)
print(df.head(3).to_string())
