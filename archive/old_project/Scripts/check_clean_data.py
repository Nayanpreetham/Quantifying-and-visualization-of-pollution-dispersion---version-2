# save as scripts/check_clean_data.py

import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('output/aqi_era5_elevation_enhanced.csv')

print("="*60)
print("DATA QUALITY CHECK")
print("="*60)

# Check for missing values
print("\nMissing values per column:")
missing = df.isnull().sum()
print(missing[missing > 0])

# Check AQI specifically
print(f"\nAQI missing values: {df['aqi'].isna().sum()}")
print(f"AQI valid values: {df['aqi'].notna().sum()}")
print(f"Total rows: {len(df)}")

# Check AQI range
print(f"\nAQI statistics:")
print(f"  Min: {df['aqi'].min()}")
print(f"  Max: {df['aqi'].max()}")
print(f"  Mean: {df['aqi'].mean():.2f}")
print(f"  Std: {df['aqi'].std():.2f}")

# Remove rows with missing AQI
df_clean = df.dropna(subset=['aqi'])

print(f"\nAfter removing missing AQI:")
print(f"  Rows removed: {len(df) - len(df_clean)}")
print(f"  Clean rows: {len(df_clean)}")

# Check other columns for missing values
print("\nMissing values in feature columns:")
feature_cols = ['t2m', 'wind_speed', 'humidity_pct', 'sp_hpa', 'blh', 
                'tp_mm', 'elevation_m', 'elevation_pblh_ratio', 
                'terrain_blocking_score', 'stagnation_index']

for col in feature_cols:
    missing_count = df_clean[col].isna().sum()
    if missing_count > 0:
        print(f"  {col}: {missing_count} missing")
        # Fill with median for numerical columns
        df_clean[col].fillna(df_clean[col].median(), inplace=True)

# Save cleaned data
df_clean.to_csv('output/aqi_clean.csv', index=False)
print(f"\n✅ Cleaned data saved to: output/aqi_clean.csv")
print(f"   Shape: {df_clean.shape}")