"""
Task 1: Verify AQI and PM2.5 Inputs and Rank Eligible Source Zones
Phase 17 — AQI-Ranked Source-to-Neighbor Pollution Transport

Formulates regulatory CPCB NAQI for PM2.5, validates 24h sample completeness,
cross-references CPCB official daily city bulletins, and ranks source zones
in descending order of AQI.
"""

import os
import glob
import pandas as pd
import numpy as np

def calculate_cpcb_naqi_pm25(concentration: float) -> tuple[float, str]:
    """
    Calculates Central Pollution Control Board (CPCB) National Air Quality Index (NAQI)
    for PM2.5 based on 24-hour average concentration (ug/m3) as per CPCB / IIT Kanpur (2014) standard.

    Breakpoints:
    0 - 30 ug/m3 -> 0 - 50 (Good)
    31 - 60 ug/m3 -> 51 - 100 (Satisfactory)
    61 - 90 ug/m3 -> 101 - 200 (Moderate)
    91 - 120 ug/m3 -> 201 - 300 (Poor)
    121 - 250 ug/m3 -> 301 - 400 (Very Poor)
    250+ ug/m3 -> 401 - 500 (Severe)
    """
    if pd.isna(concentration) or concentration < 0:
        return np.nan, "INVALID"
    
    c = float(concentration)
    if c <= 30.0:
        aqi = c * (50.0 / 30.0)
        cat = "Good"
    elif c <= 60.0:
        aqi = 50.0 + (c - 30.0) * (50.0 / 30.0)
        cat = "Satisfactory"
    elif c <= 90.0:
        aqi = 100.0 + (c - 60.0) * (100.0 / 30.0)
        cat = "Moderate"
    elif c <= 120.0:
        aqi = 200.0 + (c - 90.0) * (100.0 / 30.0)
        cat = "Poor"
    elif c <= 250.0:
        aqi = 300.0 + (c - 120.0) * (100.0 / 130.0)
        cat = "Very Poor"
    else:
        # Severe: 401 - 500
        aqi = min(500.0, 400.0 + (c - 250.0) * (100.0 / 150.0))
        cat = "Severe"
        
    return float(round(aqi, 1)), cat


def load_cpcb_city_bulletins() -> pd.DataFrame:
    """Loads official CPCB daily city bulletins from data/raw/cpcb/aqi_data/."""
    bulletin_files = glob.glob("data/raw/cpcb/aqi_data/*_AQIBulletins.csv")
    records = []
    for f in bulletin_files:
        try:
            df = pd.read_csv(f)
            df['dt'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
            records.append(df[['City', 'dt', 'Index Value', 'Air Quality', 'Prominent Pollutant']].dropna(subset=['dt']))
        except Exception:
            continue
    if records:
        all_bulletins = pd.concat(records, ignore_index=True)
        all_bulletins['date_str'] = all_bulletins['dt'].dt.strftime('%Y-%m-%d')
        return all_bulletins
    return pd.DataFrame()


def main():
    print("=== Phase 17 Task 1: Verify AQI & Rank Source Zones ===")
    
    # 1. Load Station-to-Grid Mapping
    mapping_path = "data/national/national_station_to_grid_mapping.csv"
    mapping_df = pd.read_csv(mapping_path)
    
    # The 10 core verified stations
    stations_10 = [42240, 227384, 227534, 227931, 228297, 228397, 228403, 229252, 233415, 234568]
    map_10 = mapping_df[mapping_df['station_id'].isin(stations_10)].copy()
    
    # 2. Load OpenAQ PM2.5 Observations
    openaq_path = "data/real/openaq/pm25_observations.csv"
    df_obs = pd.read_csv(openaq_path)
    df_obs['dt'] = pd.to_datetime(df_obs['timestamp_utc'])
    df_obs['date_str'] = df_obs['dt'].dt.strftime('%Y-%m-%d')
    
    # Filter to 10 stations
    obs_10 = df_obs[df_obs['station_id'].isin(stations_10)].copy()
    
    # 3. Focus on Phase 11 Multi-Week Window (2021-09-15 to 2021-10-20)
    p11_mask = (obs_10['dt'] >= '2021-09-15 00:00:00+00:00') & (obs_10['dt'] <= '2021-10-20 23:59:59+00:00')
    obs_p11 = obs_10[p11_mask].copy()
    print(f"Total observations in Phase 11 window across 10 stations: {len(obs_p11)}")
    
    # 4. Compute Daily 24-hour PM2.5 Aggregation
    daily_stats = obs_p11.groupby(['station_id', 'date_str']).agg(
        hourly_count=('pm25', 'count'),
        pm25_24h_mean=('pm25', 'mean'),
        pm25_min=('pm25', 'min'),
        pm25_max=('pm25', 'max')
    ).reset_index()
    
    # Regulatory validity: at least 16 hourly samples in 24 hours (>= 66.7% coverage)
    daily_stats['is_regulatory_valid'] = daily_stats['hourly_count'] >= 16
    daily_stats['aqi_24h'] = np.nan
    daily_stats['aqi_category'] = "INSUFFICIENT_SAMPLES"
    
    for idx, row in daily_stats.iterrows():
        if row['is_regulatory_valid']:
            aqi_val, cat = calculate_cpcb_naqi_pm25(row['pm25_24h_mean'])
            daily_stats.at[idx, 'aqi_24h'] = aqi_val
            daily_stats.at[idx, 'aqi_category'] = cat
            
    print(f"Daily station-days: {len(daily_stats)} (Valid regulatory >=16h: {daily_stats['is_regulatory_valid'].sum()})")
    
    # 5. Load CPCB City Bulletins for Cross-Reference
    bulletins_df = load_cpcb_city_bulletins()
    
    # 6. Build Summary Table per Source Station / Grid Zone
    summary_rows = []
    
    for st_id in stations_10:
        st_meta = map_10[map_10['station_id'] == st_id].iloc[0]
        st_daily = daily_stats[daily_stats['station_id'] == st_id]
        st_valid = st_daily[st_daily['is_regulatory_valid']]
        
        station_name = st_meta['station_name']
        corrected_city = st_meta['corrected_city']
        matched_grid_id = st_meta['matched_grid_id']
        st_lat = st_meta['station_latitude']
        st_lon = st_meta['station_longitude']
        grid_lat = st_meta['grid_latitude']
        grid_lon = st_meta['grid_longitude']
        distance_km = st_meta['distance_km']
        
        # OpenAQ hourly subset
        st_hourly = obs_p11[obs_p11['station_id'] == st_id]
        total_hourly_samples = len(st_hourly)
        mean_pm25 = float(st_hourly['pm25'].mean()) if len(st_hourly) > 0 else np.nan
        peak_pm25 = float(st_hourly['pm25'].max()) if len(st_hourly) > 0 else np.nan
        
        # Valid 24h regulatory metrics
        valid_days = len(st_valid)
        if valid_days > 0:
            mean_24h_pm25 = float(st_valid['pm25_24h_mean'].mean())
            mean_24h_aqi = float(st_valid['aqi_24h'].mean())
            peak_24h_aqi = float(st_valid['aqi_24h'].max())
            mean_aqi_val, mean_cat = calculate_cpcb_naqi_pm25(mean_24h_pm25)
            peak_aqi_val, peak_cat = calculate_cpcb_naqi_pm25(st_valid['pm25_24h_mean'].max())
            quality_flag = "VALID_REGULATORY_COMPLIANT_GE16_HOURLY_SAMPLES"
        else:
            mean_24h_pm25 = np.nan
            mean_24h_aqi = np.nan
            peak_24h_aqi = np.nan
            mean_cat = "NO_VALID_24H_DAYS"
            peak_cat = "NO_VALID_24H_DAYS"
            quality_flag = "INSUFFICIENT_HOURLY_SAMPLES_FOR_REGULATORY_24H_AQI"
            
        # Cross-reference city bulletin
        city_b = bulletins_df[
            (bulletins_df['City'].str.lower() == corrected_city.lower()) &
            (bulletins_df['dt'] >= '2021-09-15') &
            (bulletins_df['dt'] <= '2021-10-20')
        ] if not bulletins_df.empty else pd.DataFrame()
        
        city_bulletin_mean = float(city_b['Index Value'].mean()) if len(city_b) > 0 else np.nan
        city_bulletin_peak = float(city_b['Index Value'].max()) if len(city_b) > 0 else np.nan
        
        summary_rows.append({
            'station_id': int(st_id),
            'station_name': station_name,
            'city': corrected_city,
            'source_grid_id': matched_grid_id,
            'station_latitude': round(st_lat, 4),
            'station_longitude': round(st_lon, 4),
            'grid_latitude': round(grid_lat, 4),
            'grid_longitude': round(grid_lon, 4),
            'station_grid_distance_km': round(distance_km, 2),
            'study_period': '2021-09-15 to 2021-10-20',
            'hourly_samples_count': total_hourly_samples,
            'valid_regulatory_days_count': valid_days,
            'hourly_pm25_mean_ugm3': round(mean_pm25, 2),
            'hourly_pm25_peak_ugm3': round(peak_pm25, 2),
            'regulatory_24h_pm25_mean_ugm3': round(mean_24h_pm25, 2) if not np.isnan(mean_24h_pm25) else np.nan,
            'regulatory_24h_aqi_mean': round(mean_24h_aqi, 1) if not np.isnan(mean_24h_aqi) else np.nan,
            'regulatory_24h_aqi_peak': round(peak_24h_aqi, 1) if not np.isnan(peak_24h_aqi) else np.nan,
            'aqi_category_mean': mean_cat,
            'aqi_category_peak': peak_cat,
            'cpcb_city_bulletin_aqi_mean': round(city_bulletin_mean, 1) if not np.isnan(city_bulletin_mean) else np.nan,
            'cpcb_city_bulletin_aqi_peak': round(city_bulletin_peak, 1) if not np.isnan(city_bulletin_peak) else np.nan,
            'aqi_standard': 'CPCB_NAQI_2014_24H_PM25',
            'data_quality_flag': quality_flag
        })
        
    df_ranked = pd.DataFrame(summary_rows)
    
    # Rank descending by regulatory_24h_aqi_mean
    # If tie or NaN, sort by hourly_pm25_mean_ugm3
    df_ranked = df_ranked.sort_values(
        by=['regulatory_24h_aqi_mean', 'hourly_pm25_mean_ugm3'],
        ascending=[False, False]
    ).reset_index(drop=True)
    
    # Assign AQI rank
    df_ranked.insert(0, 'aqi_rank', range(1, len(df_ranked) + 1))
    
    # Save output table
    out_path = "results/phase17_target_zones/source_zones_ranked_by_aqi.csv"
    df_ranked.to_csv(out_path, index=False)
    print(f"\nSaved ranked source zones to: {out_path}")
    print("\nRanked Source Zones Preview:")
    cols_show = ['aqi_rank', 'city', 'station_id', 'source_grid_id', 'regulatory_24h_aqi_mean', 'aqi_category_mean', 'regulatory_24h_aqi_peak', 'hourly_pm25_mean_ugm3', 'cpcb_city_bulletin_aqi_mean']
    print(df_ranked[cols_show].to_string(index=False))


if __name__ == '__main__':
    main()
