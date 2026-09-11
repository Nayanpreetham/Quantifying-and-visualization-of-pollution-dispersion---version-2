"""
Terminal AQI Prediction with Component Breakdown
- Always predicts for 2024 + horizon
- India boundary check
- Components: Meteorological, Stagnation, Dispersion
"""

import sys
import os
import warnings
import numpy as np

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Scripts'))

from prediction.predict_aqi import predict_aqi
from prediction.generate_report import aqi_category

# India boundaries
INDIA_LAT_MIN, INDIA_LAT_MAX = 6.0, 38.0
INDIA_LON_MIN, INDIA_LON_MAX = 68.0, 97.0

def is_in_india(lat, lon):
    return INDIA_LAT_MIN <= lat <= INDIA_LAT_MAX and INDIA_LON_MIN <= lon <= INDIA_LON_MAX

def horizon_to_target_date(horizon_str, ref_year=2024, ref_month=1, ref_day=1):
    """Convert horizon to target (year, month)."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    ref = datetime(ref_year, ref_month, ref_day)
    h = horizon_str.lower()
    if h == "15 days":
        target = ref + relativedelta(days=15)
    elif h == "1 month":
        target = ref + relativedelta(months=1)
    elif h == "3 months":
        target = ref + relativedelta(months=3)
    elif h == "6 months":
        target = ref + relativedelta(months=6)
    elif h == "1 year":
        target = ref + relativedelta(years=1)
    else:
        raise ValueError(f"Unknown horizon: {horizon_str}")
    return target.year, target.month

def compute_stagnation_impact(baseline_aqi, wind_speed, blh):
    """
    Stagnation Impact = baseline * stagnation_factor
    stagnation_factor = min(0.5, stagnation_index / 10)
    stagnation_index = 1 / (wind_speed * blh + 1e-6)
    """
    ventilation = wind_speed * blh
    stagnation_index = 1.0 / (ventilation + 1e-6)
    stagnation_factor = min(0.5, stagnation_index / 10.0)
    return baseline_aqi * stagnation_factor

def main():
    print("\n" + "="*60)
    print(" AQI PREDICTION SYSTEM ")
    print("="*60)

    # ---- Get location ----
    try:
        lat = float(input("📍 Enter Latitude (°N): "))
        lon = float(input("📍 Enter Longitude (°E): "))
    except ValueError:
        print("❌ Invalid number. Please enter numeric values.")
        return

    if not is_in_india(lat, lon):
        print("❌ Out of India boundary. Lat must be 6–38°N, Lon 68–97°E.")
        return

    # ---- Get horizon ----
    valid_horizons = ["15 days", "1 month", "3 months", "6 months", "1 year"]
    print("\n⏱️ Prediction horizon options:")
    for opt in valid_horizons:
        print(f"   • {opt}")
    horizon = input("Choose (exactly as shown): ").strip().lower()

    if horizon not in [h.lower() for h in valid_horizons]:
        print("❌ Typo mistake. Please choose from: " + ", ".join(valid_horizons))
        return

    matched = next(h for h in valid_horizons if h.lower() == horizon)

    # ---- Target date (always based on 2024) ----
    try:
        year, month = horizon_to_target_date(matched, ref_year=2024, ref_month=1, ref_day=1)
    except ImportError:
        print("Installing python-dateutil...")
        os.system("pip install python-dateutil")
        from dateutil.relativedelta import relativedelta
        year, month = horizon_to_target_date(matched)

    print(f"\n🔮 Predicting for {lat:.2f}°N, {lon:.2f}°E")
    print(f"   Horizon: {matched} → {year}-{month:02d} (target date)")

    # ---- Run prediction ----
    try:
        result = predict_aqi(lat, lon, month, year)
    except Exception as e:
        print(f"❌ Prediction failed: {e}")
        return

    # Extract values
    baseline_aqi = result['baseline_aqi']           # Meteorological AQI
    spatial_effect = result['spatial_effect']       # Dispersion Impact
    features = result['features']
    wind_speed = features['wind_speed']
    blh = features['blh']
    station_effects = result['station_effects'][:3]

    # ---- Compute Stagnation Impact ----
    stagnation_impact = compute_stagnation_impact(baseline_aqi, wind_speed, blh)

    # ---- Final Predicted AQI ----
    predicted_aqi = baseline_aqi + stagnation_impact + spatial_effect

    # ---- Output ----
    print("\n" + "-"*50)
    print("📊 AQI COMPONENT BREAKDOWN")
    print("-"*50)
    print(f"🌦️  Meteorological AQI     = {baseline_aqi:.0f}  (weather + elevation + seasonal)")
    print(f"🌫️  Stagnation Impact      = {stagnation_impact:+.0f}  (extra due to poor dispersion)")
    print(f"🌬️  Dispersion Impact      = {spatial_effect:+.0f}  (net effect from nearby cities)")
    print("-"*50)
    print(f"🔮 PREDICTED AQI           = {predicted_aqi:.0f}  ({aqi_category(predicted_aqi)})")
    print("-"*50)

    # ---- Dispersion table (top 3 cities) ----
    print("\n🌬️  NEARBY CITY DISPERSION (top 3)")
    print("     Positive = adds to your AQI, Negative = removes")
    print(f"{'City':<15} {'Distance (km)':<13} {'Effect (AQI)':<12} {'Wind Relation'}")
    print("-" * 55)
    for e in station_effects:
        effect = e['raw_effect']   # raw effect before alpha scaling (proportional)
        print(f"{e['station']:<15} {e['distance']:<13.1f} {effect:+8.1f}       {e['wind_rel']}")

    print("\n" + "="*60)
    print("✅ Prediction complete.")

if __name__ == "__main__":
    # Ensure dateutil is installed
    try:
        from dateutil.relativedelta import relativedelta
    except ImportError:
        print("Installing python-dateutil...")
        os.system("pip install python-dateutil")
        from dateutil.relativedelta import relativedelta
    main()