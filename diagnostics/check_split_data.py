"""Check the actual data in E06000061 and E06000062"""
from data_loading import load_wellbeing_data
from boundaries import harmonise_boundaries, remap_scottish_codes

wb = load_wellbeing_data()
wb = harmonise_boundaries(wb)
wb = remap_scottish_codes(wb)

print("NORTH NORTHAMPTONSHIRE (E06000061)")
print("=" * 70)

north = wb[wb['la_code'] == 'E06000061']
print(f"Total rows: {len(north)}")

north_ls = north[north['measure'] == 'life-satisfaction'].sort_values('year')
print("\nLife satisfaction:")
print(north_ls[['year', 'value']])

print("\n" + "=" * 70)
print("WEST NORTHAMPTONSHIRE (E06000062)")
print("=" * 70)

west = wb[wb['la_code'] == 'E06000062']
print(f"Total rows: {len(west)}")

west_ls = west[west['measure'] == 'life-satisfaction'].sort_values('year')
print("\nLife satisfaction:")
print(west_ls[['year', 'value']])

print("\n" + "=" * 70)
print("ANALYSIS")
print("=" * 70)

# Check which years have data in BOTH
north_years = set(north_ls[north_ls['value'].notna()]['year'])
west_years = set(west_ls[west_ls['value'].notna()]['year'])

print(f"\nNorth has data for years: {sorted(north_years)}")
print(f"West has data for years: {sorted(west_years)}")
print(f"Both have data for years: {sorted(north_years & west_years)}")

if len(north_years & west_years) < 6:
    print(f"\n✗ Problem: Only {len(north_years & west_years)} overlapping years")
    print("  combine_splits() can only compute mean when BOTH have data")
    print("  Years 2011-2018 likely have NaN in one or both parts")
