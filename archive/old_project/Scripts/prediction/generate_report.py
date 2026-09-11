"""
Generate formatted prediction report.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prediction.predict_aqi import predict_aqi


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


def format_report_string(lat, lon, elevation, month, year, horizon_desc, 
                         final_aqi, baseline_aqi, spatial_effect, 
                         features, wind_dir, station_effects):
    """Generate formatted report as a string for GUI display."""
    category = aqi_category(final_aqi)
    
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    month_name = month_names[month - 1]
    
    lines = []
    lines.append("=" * 70)
    lines.append("  VAHAN PREDICTION REPORT")
    lines.append(f"  LOCATION : {lat:.2f}°N, {lon:.2f}°E")
    lines.append(f"  ELEVATION: {elevation:.0f} m")
    lines.append(f"  HORIZON  : {horizon_desc} ({month_name} {year})")
    lines.append(f"  PREDICTED AQI : {final_aqi:.0f} — \"{category}\"")
    lines.append("=" * 70)
    
    lines.append("\n🌡️ METEOROLOGICAL CONDITIONS")
    lines.append(f"  Temperature: {features['t2m']:.1f}°C")
    lines.append(f"  Humidity: {features['humidity_pct']:.1f}%")
    lines.append(f"  Wind Speed: {features['wind_speed']:.1f} m/s")
    lines.append(f"  Wind Direction: {wind_dir:.0f}°")
    lines.append(f"  Pressure: {features['sp_hpa']:.0f} hPa")
    lines.append(f"  Boundary Layer: {features['blh']:.0f} m")
    lines.append(f"  Precipitation: {features['tp_mm']:.1f} mm")
    
    lines.append("\n🌬️ SPATIAL CONTRIBUTION (TOP 6 NEARBY STATIONS)")
    lines.append("Effect indicates AQI change at your location attributable to this station.\n")
    
    if station_effects:
        lines.append(f"{'Station':<12} {'Distance':<10} {'Direction':<12} {'Wind Rel.':<12} {'Station AQI':<12} {'Effect':<10}")
        lines.append(f"{'':12} {'(km)':<10} {'(Bearing)':<12} {'':12} {'':12} {'(AQI Units)':<10}")
        lines.append("-" * 70)
        
        for e in station_effects:
            direction = bearing_to_compass(e['bearing'])
            wind_symbol = {'UPWIND': '⬆️ UPWIND', 'DOWNWIND': '⬇️ DOWNWIND', 'CROSS': '➡️ CROSS'}[e['wind_rel']]
            effect_str = f"{e['raw_effect']:+.0f}"
            lines.append(f"{e['station']:<12} {e['distance']:<10.0f} {direction:<12} {wind_symbol:<12} {e['station_aqi']:<12.0f} {effect_str:<10}")
    else:
        lines.append("  No nearby stations found within range.")
    
    lines.append("\n📊 FINAL AQI COMPOSITION")
    lines.append(f"  Baseline (weather + elevation) : {baseline_aqi:.0f}")
    lines.append(f"  Spatial Adjustment            : {spatial_effect:+.0f}")
    lines.append(f"  TOTAL                         : {final_aqi:.0f}")
    
    lines.append("\n" + "=" * 70)
    
    return "\n".join(lines)


def generate_report_to_string(lat, lon, month, year=2023, horizon_desc="1 Month Climatology"):
    """Generate report and return as string."""
    result = predict_aqi(lat, lon, month, year)
    
    return format_report_string(
        lat=lat,
        lon=lon,
        elevation=result['location']['elevation'],
        month=month,
        year=year,
        horizon_desc=horizon_desc,
        final_aqi=result['final_aqi'],
        baseline_aqi=result['baseline_aqi'],
        spatial_effect=result['spatial_effect'],
        features=result['features'],
        wind_dir=result['wind_dir'],
        station_effects=result['station_effects']
    )


def generate_report(lat, lon, month, year=2023, horizon_desc="1 Month Climatology"):
    """Generate and print the full prediction report."""
    report = generate_report_to_string(lat, lon, month, year, horizon_desc)
    print(report)


if __name__ == "__main__":
    # Example: Predict for Delhi in January
    generate_report(28.6139, 77.2090, month=1, year=2023, horizon_desc="1 Month Climatology")