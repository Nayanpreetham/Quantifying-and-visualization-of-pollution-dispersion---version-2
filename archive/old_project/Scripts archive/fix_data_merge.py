# save as scripts/fix_data_merge.py

import pandas as pd
import numpy as np

print("="*60)
print("FIXING DATA MERGE - KEEP ALL WEATHER DATA")
print("="*60)

# Load your original merged data
df = pd.read_csv('output/aqi_era5_elevation_enhanced.csv')

print(f"\nOriginal shape: {df.shape}")
print(f"Original columns: {df.columns.tolist()}")

# Check what's missing
print(f"\nAQI missing: {df['aqi'].isna().sum():,} rows")
print(f"AQI present: {df['aqi'].notna().sum():,} rows")

# Option 1: Keep all rows, AQI can be NaN for prediction
# This is CORRECT - you need weather data for all days
df_with_nan = df.copy()

# Fill elevation features (these should be per city, not per day)
# For each city, elevation is constant, so forward fill within city
df_with_nan['elevation_m'] = df_with_nan.groupby('city')['elevation_m'].transform(lambda x: x.ffill().bfill())
df_with_nan['elevation_source'] = df_with_nan.groupby('city')['elevation_source'].transform(lambda x: x.ffill().bfill())
df_with_nan['terrain_category'] = df_with_nan.groupby('city')['terrain_category'].transform(lambda x: x.ffill().bfill())

# For weather variables, fill with reasonable defaults if needed
weather_cols = ['t2m', 'wind_speed', 'humidity_pct', 'sp_hpa', 'blh', 'tp_mm']
for col in weather_cols:
    # Fill with city's median for that variable
    df_with_nan[col] = df_with_nan.groupby('city')[col].transform(lambda x: x.fillna(x.median()))

print(f"\n✅ After filling: {df_with_nan.isna().sum().sum()} total missing values")

# Save the fixed dataset (keep all 404k rows)
df_with_nan.to_csv('output/aqi_weather_complete.csv', index=False)
print(f"\n✅ Saved complete dataset: output/aqi_weather_complete.csv")
print(f"   Shape: {df_with_nan.shape}")
print(f"   AQI available: {df_with_nan['aqi'].notna().sum():,} days")
print(f"   Weather only (no AQI): {df_with_nan['aqi'].isna().sum():,} days")

# For training, you'll use only rows with AQI
# For prediction, you'll use all rows
print("\n" + "="*60)
print("CORRECT APPROACH:")
print("="*60)
print("""
1. TRAINING: Use only rows with AQI values (4,503 rows)
   - Train model on these to learn AQI patterns

2. PREDICTION: Use ALL weather rows (404,697 rows)
   - Predict AQI for every day at every city
   - This is what you originally wanted!

3. Keep elevation features (they're city-specific constants)
""")