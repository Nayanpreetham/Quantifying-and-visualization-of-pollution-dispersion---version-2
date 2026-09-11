"""
Generate formatted prediction report.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prediction.predict_aqi import predict_aqi

def format_report_string(lat, lon, month, year=2023, horizon_desc="1 Month Climatology", elevation=None):
    """Return the full prediction result dictionary.
    
    Returns:
        dict with keys: final_aqi, baseline_aqi, spatial_effect, features, wind_dir, station_effects
    """
    result = predict_aqi(lat, lon, month, year)
    
    return {
        'final_aqi': result['final_aqi'],
        'baseline_aqi': result['baseline_aqi'],
        'spatial_effect': result['spatial_effect'],
        'features': result['features'],
        'wind_dir': result['wind_dir'],
        'station_effects': result['station_effects']
    }

def aqi_category(aqi):
    """Return AQI category based on Indian NAQI standards."""
    if aqi <= 50:
        return "GOOD"
    elif aqi <= 100:
        return "SATISFACTORY"
    elif aqi <= 200:
        return "MODERATE"
    elif aqi <= 300:
        return "POOR"
    elif aqi <= 400:
        return "VERY POOR"
    else:
        return "SEVERE"

def bearing_to_compass(bearing):
    """Convert bearing to compass direction."""
    compass = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    idx = int((bearing + 22.5) // 45) % 8
    return f"{bearing:.0f}° {compass[idx]}"

def generate_report(lat, lon, month, year=2023, horizon_desc="1 Month Climatology"):
    """Generate and print the full prediction report."""
    result = predict_aqi(lat, lon, month, year)
    
    final_aqi = result['final_aqi']
    category = aqi_category(final_aqi)
    
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    month_name = month_names[month - 1]
    
    print("=" * 70)
    print("  VAHAN PREDICTION REPORT")
    print(f"  LOCATION : {lat:.2f}°N, {lon:.2f}°E")
    print(f"  ELEVATION: {result['location']['elevation']:.0f} m")
    print(f"  HORIZON  : {horizon_desc} ({month_name} {year})")
    print(f"  PREDICTED AQI : {final_aqi:.0f} — \"{category}\"")
    print("=" * 70)
    
    # Meteorological summary
    print("\n🌡️ METEOROLOGICAL CONDITIONS")
    f = result['features']
    print(f"  Temperature: {f['t2m']:.1f}°C")
    print(f"  Humidity: {f['humidity_pct']:.1f}%")
    print(f"  Wind Speed: {f['wind_speed']:.1f} m/s")
    print(f"  Wind Direction: {result['wind_dir']:.0f}°")
    print(f"  Pressure: {f['sp_hpa']:.0f} hPa")
    print(f"  Boundary Layer: {f['blh']:.0f} m")
    print(f"  Precipitation: {f['tp_mm']:.1f} mm")
    
    # Spatial contribution
    print("\n🌬️ SPATIAL CONTRIBUTION (TOP 6 NEARBY STATIONS)")
    print("Effect indicates AQI change at your location attributable to this station.\n")
    
    station_effects = result['station_effects']
    if station_effects:
        print(f"{'Station':<12} {'Distance':<10} {'Direction':<12} {'Wind Rel.':<12} {'Station AQI':<12} {'Effect':<10}")
        print(f"{'':12} {'(km)':<10} {'(Bearing)':<12} {'':12} {'':12} {'(AQI Units)':<10}")
        print("-" * 70)
        
        for e in station_effects:
            direction = bearing_to_compass(e['bearing'])
            wind_symbol = {'UPWIND': '⬆️ UPWIND', 'DOWNWIND': '⬇️ DOWNWIND', 'CROSS': '➡️ CROSS'}[e['wind_rel']]
            effect_str = f"{e['raw_effect']:+.0f}"
            print(f"{e['station']:<12} {e['distance']:<10.0f} {direction:<12} {wind_symbol:<12} {e['station_aqi']:<12.0f} {effect_str:<10}")
    else:
        print("  No nearby stations found within range.")
    
    # Final composition
    print("\n📊 FINAL AQI COMPOSITION")
    print(f"  Baseline (weather + elevation) : {result['baseline_aqi']:.0f}")
    print(f"  Spatial Adjustment            : {result['spatial_effect']:+.0f}")
    print(f"  TOTAL                         : {final_aqi:.0f}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    # Example: Predict for Delhi in January
    generate_report(28.6139, 77.2090, month=1, year=2023, horizon_desc="1 Month Climatology")