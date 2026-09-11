"""
Calibrate spatial adjustment parameters.
"""

import pandas as pd
import numpy as np
import json
import os

# Geo functions defined inline
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def bearing_to_station(lat1, lon1, lat2, lon2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    x = np.sin(dlambda) * np.cos(phi2)
    y = np.cos(phi1)*np.sin(phi2) - np.sin(phi1)*np.cos(phi2)*np.cos(dlambda)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360

def wind_alignment_weight(wind_dir, bearing_to):
    delta = (wind_dir - bearing_to + 180) % 360 - 180
    return np.cos(np.radians(delta))

# Paths
INPUT_CSV = "final clean/training_features_processed.csv"
STATION_CLIM_CSV = "final clean/station_monthly_climatology.csv"
OUTPUT_JSON = "Models/spatial_params.json"

DEFAULT_L = 200
MAX_DISTANCE = 500

def main():
    print("Loading data...")
    df = pd.read_csv(INPUT_CSV)
    df['date'] = pd.to_datetime(df['date'])
    station_clim = pd.read_csv(STATION_CLIM_CSV)

    station_coords = station_clim[['city', 'lat', 'lon']].drop_duplicates().set_index('city')

    # Sample subset for calibration
    sample_df = df.iloc[::100].copy()
    sample_df['month'] = df['date'].dt.month

    print(f"Calibrating on {len(sample_df)} samples...")

    residuals = []
    sum_raw_effects = []

    # Use average wind direction if not available
    default_wind_dir = 270  # westerly

    for idx, row in sample_df.iterrows():
        target_lat = row['lat']
        target_lon = row['lon']
        target_month = row['month']
        wind_dir = row.get('wind_dir', default_wind_dir)
        actual_aqi = row['aqi']

        # Simple baseline: monthly average AQI
        baseline_aqi = df[df['month'] == target_month]['aqi'].mean()
        residual = actual_aqi - baseline_aqi

        total_raw_effect = 0.0
        for station_city, station_data in station_coords.iterrows():
            clim_row = station_clim[(station_clim['city'] == station_city) &
                                    (station_clim['month'] == target_month)]
            if len(clim_row) == 0:
                continue

            distance = haversine_distance(target_lat, target_lon,
                                          station_data['lat'], station_data['lon'])
            if distance > MAX_DISTANCE:
                continue

            station_aqi = clim_row['aqi'].values[0]
            bearing_to = bearing_to_station(target_lat, target_lon,
                                            station_data['lat'], station_data['lon'])
            w = wind_alignment_weight(wind_dir, bearing_to)
            decay = np.exp(-distance / DEFAULT_L)

            total_raw_effect += station_aqi * w * decay

        residuals.append(residual)
        sum_raw_effects.append(total_raw_effect)

    # Simple linear regression
    X = np.array(sum_raw_effects)
    y = np.array(residuals)

    if np.sum(X**2) > 0:
        alpha = np.sum(X * y) / np.sum(X**2)
    else:
        alpha = 0.1

    intercept = np.mean(y) - alpha * np.mean(X)

    params = {
        'alpha': float(alpha),
        'intercept': float(intercept),
        'L': DEFAULT_L,
        'max_distance': MAX_DISTANCE
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(params, f, indent=2)

    print(f"\n✅ Saved spatial parameters to: {OUTPUT_JSON}")
    print(f"   Alpha: {alpha:.4f}, Intercept: {intercept:.2f}")

if __name__ == "__main__":
    main()