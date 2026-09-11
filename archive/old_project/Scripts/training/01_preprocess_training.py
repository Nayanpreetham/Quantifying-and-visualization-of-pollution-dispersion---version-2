"""
Preprocess the training data by merging with ERA5 wind components.
"""

import pandas as pd
import numpy as np
import os

# Paths
INTERMEDIATE_CSV = "Intermediate/aqi_era5_merged.csv"
FINAL_CSV = "final clean/aqi_final_clean_weighted.csv"
OUTPUT_CSV = "final clean/training_features_processed.csv"

def main():
    print("Loading data...")
    
    # Load the intermediate file (has ERA5 data with u10, v10)
    # Date format is dd-mm-yyyy
    df_intermediate = pd.read_csv(INTERMEDIATE_CSV)
    df_intermediate['date'] = pd.to_datetime(df_intermediate['date'], dayfirst=True)
    print(f"Intermediate file: {len(df_intermediate)} rows")
    
    # Load the final file (has derived indices)
    df_final = pd.read_csv(FINAL_CSV)
    df_final['date'] = pd.to_datetime(df_final['date'], dayfirst=True)
    print(f"Final file: {len(df_final)} rows")
    
    # Identify key columns to merge on
    merge_cols = ['date', 'city', 'lat', 'lon']
    
    # Get u10, v10 from intermediate
    wind_cols = ['u10', 'v10']
    available_wind = [col for col in wind_cols if col in df_intermediate.columns]
    
    if len(available_wind) == 2:
        print(f"Found wind components: {available_wind}")
        # Keep only needed columns to avoid duplicate column issues
        cols_to_keep = merge_cols + available_wind
        wind_data = df_intermediate[cols_to_keep].copy()
        
        # Merge with final dataframe
        df = df_final.merge(wind_data, on=merge_cols, how='left')
        print(f"Merged data: {len(df)} rows")
        
        # Compute wind direction
        df['wind_dir'] = np.degrees(np.arctan2(df['v10'], df['u10']))
        df['wind_dir'] = (270 - df['wind_dir']) % 360
        
        # Create cyclical features
        df['wind_dir_sin'] = np.sin(2 * np.pi * df['wind_dir'] / 360)
        df['wind_dir_cos'] = np.cos(2 * np.pi * df['wind_dir'] / 360)
        
        print("Wind direction computed successfully.")
    else:
        print(f"Wind components not found. Available: {available_wind}")
        df = df_final.copy()
        df['wind_dir'] = 180
        df['wind_dir_sin'] = 0.0
        df['wind_dir_cos'] = -1.0
    
    # Extract month and create cyclical features
    df['month'] = df['date'].dt.month
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    
    # Drop rows with NaN in critical columns
    critical_cols = ['aqi', 't2m', 'wind_speed', 'humidity_pct', 'sp_hpa', 'blh']
    before_drop = len(df)
    df = df.dropna(subset=[c for c in critical_cols if c in df.columns])
    print(f"After dropping NaNs: {len(df)} rows (dropped {before_drop - len(df)})")
    
    # Save processed data
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✅ Saved processed data to: {OUTPUT_CSV}")
    print(f"   Final columns ({len(df.columns)}):")
    for col in df.columns:
        print(f"     - {col}")

if __name__ == "__main__":
    main()