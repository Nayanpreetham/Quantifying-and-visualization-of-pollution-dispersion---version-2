"""
Main prediction script for a new location.
Combines baseline model prediction and spatial adjustment.
"""

import numpy as np
import pandas as pd
import joblib
import json
import os
import sys

# Add Scripts to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prediction.fetch_elevation import get_elevation
from prediction.fetch_meteo import get_monthly_climatology

# Paths
MODEL_DIR = "Models"
MODEL_PATH = f"{MODEL_DIR}/aqi_baseline_model.pkl"
SCALER_PATH = f"{MODEL_DIR}/scaler.pkl"
FEATURE_COLS_PATH = f"{MODEL_DIR}/feature_columns.pkl"
SPATIAL_PARAMS_PATH = f"{MODEL_DIR}/spatial_params.json"
STATION_CLIM_PATH = "final clean/station_monthly_climatology.csv"

def load_models():
    """Load trained model, scaler, and spatial params."""
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    feature_cols = joblib.load(FEATURE_COLS_PATH)
    
    with open(SPATIAL_PARAMS_PATH, 'r') as f:
        spatial_params = json.load(f)
    
    station_clim = pd.read_csv(STATION_CLIM_PATH)
    
    return model, scaler, feature_cols, spatial_params, station_clim

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

def bearing_to_station(lat1, lon1, lat2, lon2):
    """Calculate bearing from target to station (0-360°)."""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlambda = np.radians(lon2 - lon1)
    x = np.sin(dlambda) * np.cos(phi2)
    y = np.cos(phi1)*np.sin(phi2) - np.sin(phi1)*np.cos(phi2)*np.cos(dlambda)
    return (np.degrees(np.arctan2(x, y)) + 360) % 360

def wind_alignment_weight(wind_dir, bearing_to):
    """Calculate wind transport alignment weight."""
    delta = (wind_dir - bearing_to + 180) % 360 - 180
    return np.cos(np.radians(delta))

def compute_spatial_effect(target_lat, target_lon, target_month, wind_dir,
                           station_clim, spatial_params):
    """Compute total spatial adjustment from nearby stations."""
    alpha = spatial_params['alpha']
    intercept = spatial_params['intercept']
    L = spatial_params['L']
    max_dist = spatial_params['max_distance']
    
    station_coords = station_clim[['city', 'lat', 'lon']].drop_duplicates().set_index('city')
    station_effects = []
    total_raw_effect = 0.0
    
    for station_city, station_data in station_coords.iterrows():
        distance = haversine_distance(target_lat, target_lon,
                                      station_data['lat'], station_data['lon'])
        if distance > max_dist:
            continue
        
        clim_row = station_clim[(station_clim['city'] == station_city) &
                                (station_clim['month'] == target_month)]
        if len(clim_row) == 0:
            continue
        
        station_aqi = clim_row['aqi'].values[0]
        bearing_to = bearing_to_station(target_lat, target_lon,
                                        station_data['lat'], station_data['lon'])
        w = wind_alignment_weight(wind_dir, bearing_to)
        decay = np.exp(-distance / L)
        raw_effect = station_aqi * w * decay
        
        total_raw_effect += raw_effect
        
        # Determine wind relation
        delta = (wind_dir - bearing_to + 180) % 360 - 180
        if abs(delta) <= 45:
            wind_rel = "UPWIND"
        elif abs(delta) >= 135:
            wind_rel = "DOWNWIND"
        else:
            wind_rel = "CROSS"
        
        station_effects.append({
            'station': station_city,
            'distance': distance,
            'bearing': bearing_to,
            'wind_rel': wind_rel,
            'station_aqi': station_aqi,
            'raw_effect': raw_effect
        })
    
    total_spatial_effect = alpha * total_raw_effect + intercept
    station_effects.sort(key=lambda x: abs(x['raw_effect']), reverse=True)
    
    return total_spatial_effect, station_effects[:6]

def compute_derived_indices(elevation_m, blh, wind_speed):
    """Compute derived indices from base variables."""
    blh_safe = max(blh, 1.0)
    
    return {
        'elevation_pblh_ratio': elevation_m / blh_safe,
        'ventilation_index': wind_speed * blh_safe,
        'stagnation_index': 1.0 / (wind_speed * blh_safe + 1e-6),
        'dispersion_potential': (wind_speed * blh_safe) / 1000.0,
        'terrain_blocking_score': (elevation_m / 1000.0) / (wind_speed + 0.5)
    }

def predict_aqi(lat, lon, month, year=2023):
    """Main prediction function."""
    # Load models
    model, scaler, feature_cols, spatial_params, station_clim = load_models()
    
    # Get elevation
    elevation_m = get_elevation(lat, lon)
    
    # Get meteorology
    meteo = get_monthly_climatology(lat, lon, month, year)
    
    # Compute wind direction
    wind_dir = np.degrees(np.arctan2(meteo['v10'], meteo['u10']))
    wind_dir = (270 - wind_dir) % 360
    
    # Compute derived indices
    derived = compute_derived_indices(elevation_m, meteo['blh'], meteo['wind_speed'])
    
    # Prepare feature dictionary
    features = {
        't2m': meteo['t2m'],
        'wind_speed': meteo['wind_speed'],
        'humidity_pct': meteo['humidity_pct'],
        'sp_hpa': meteo['sp_hpa'],
        'blh': meteo['blh'],
        'tp_mm': meteo['tp_mm'],
        'elevation_m': elevation_m,
        'elevation_pblh_ratio': derived['elevation_pblh_ratio'],
        'stagnation_index': derived['stagnation_index'],
        'dispersion_potential': derived['dispersion_potential'],
        'terrain_blocking_score': derived['terrain_blocking_score'],
        'ventilation_index': derived['ventilation_index'],
        'wind_dir_sin': np.sin(2 * np.pi * wind_dir / 360),
        'wind_dir_cos': np.cos(2 * np.pi * wind_dir / 360),
        'month_sin': np.sin(2 * np.pi * month / 12),
        'month_cos': np.cos(2 * np.pi * month / 12)
    }
    
    # Create feature vector in correct order
    feature_vector = np.array([[features.get(col, 0) for col in feature_cols]])
    
    # Scale and predict baseline
    feature_vector_scaled = scaler.transform(feature_vector)
    baseline_aqi = model.predict(feature_vector_scaled)[0]
    
    # Compute spatial effect
    spatial_effect, station_effects = compute_spatial_effect(
        lat, lon, month, wind_dir, station_clim, spatial_params
    )
    
    # Final AQI
    final_aqi = baseline_aqi + spatial_effect
    
    return {
        'baseline_aqi': baseline_aqi,
        'spatial_effect': spatial_effect,
        'final_aqi': final_aqi,
        'station_effects': station_effects,
        'features': features,
        'location': {'lat': lat, 'lon': lon, 'elevation': elevation_m},
        'month': month,
        'year': year,
        'wind_dir': wind_dir
    }

if __name__ == "__main__":
    # Test prediction for Delhi in January
    print("Testing AQI prediction for Delhi (January):")
    print("-" * 50)
    result = predict_aqi(28.6139, 77.2090, month=1, year=2023)
    print(f"Baseline AQI: {result['baseline_aqi']:.0f}")
    print(f"Spatial effect: {result['spatial_effect']:+.0f}")
    print(f"Final AQI: {result['final_aqi']:.0f}")