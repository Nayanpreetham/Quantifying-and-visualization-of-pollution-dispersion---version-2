"""
Build monthly AQI climatology for each station.
"""

import pandas as pd
import os

INPUT_CSV = "final clean/training_features_processed.csv"
OUTPUT_CSV = "final clean/station_monthly_climatology.csv"

def main():
    print("Loading processed data...")
    df = pd.read_csv(INPUT_CSV)
    df['date'] = pd.to_datetime(df['date'])
    print(f"Loaded {len(df)} rows")

    # Get station coordinates (average lat/lon per city)
    coord_cols = ['city', 'lat', 'lon', 'elevation_m']
    available_coords = [c for c in coord_cols if c in df.columns]
    station_coords = df[available_coords].groupby('city').mean().reset_index()

    # Compute monthly average AQI per station
    df['month'] = df['date'].dt.month
    monthly_aqi = df.groupby(['city', 'month'])['aqi'].mean().reset_index()
    monthly_aqi['aqi'] = monthly_aqi['aqi'].round(0).astype(int)

    # Merge with coordinates
    climatology = monthly_aqi.merge(station_coords, on='city')

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    climatology.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Saved station climatology to: {OUTPUT_CSV}")
    print(f"   {len(station_coords)} stations, {len(monthly_aqi)} station-month records")

if __name__ == "__main__":
    main()