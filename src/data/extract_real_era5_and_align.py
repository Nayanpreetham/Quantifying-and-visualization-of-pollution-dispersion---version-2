"""
EXTRACT REAL ERA5 WIND & ALIGN WITH OPENAQ PM2.5
================================================
Step 2 & Step 3 of Real Data Pipeline:
- Extracts u10 and v10 from data/raw/era5/2021/era5_2021_instant.nc
- Defines 7x7 spatial grid for 5 pilot cities (Agra, Kanpur, Varanasi, Chandigarh, Ahmedabad)
- Maps OpenAQ monitoring stations to spatial grid cells
- Aligns real OpenAQ hourly PM2.5 observations with real ERA5 surface winds
- Preserves all physical units: PM2.5 in ug/m3, wind u10/v10 in m/s

Outputs:
- data/real/era5/era5_u10_v10_pilot.nc
- data/real/era5/era5_wind.csv
- data/processed/real_grid.csv
- data/processed/station_to_grid_mapping.csv
- data/processed/openaq_pm25_grid.csv
- data/processed/openaq_era5_aligned.csv
"""

import os
import numpy as np
import pandas as pd
import xarray as xr

DATA_LABEL = "REAL DATA — OPENAQ OBSERVATIONS & ERA5 REANALYSIS"

PILOT_CITIES = [
    {"city_id": "AGR", "name": "Agra",       "lat": 27.1987, "lon": 78.0060},
    {"city_id": "KNP", "name": "Kanpur",     "lat": 26.4703, "lon": 80.3230},
    {"city_id": "VNS", "name": "Varanasi",   "lat": 25.3176, "lon": 82.9739},
    {"city_id": "IXC", "name": "Chandigarh", "lat": 30.7356, "lon": 76.7757},
    {"city_id": "AMD", "name": "Ahmedabad",  "lat": 23.0225, "lon": 72.5714},
]

GRID_DIM = 7        # 7x7 grid per city = 49 cells per city (245 total)
GRID_SPACING = 0.1  # 0.1 degree spacing (~11 km)
START_TIME = "2021-09-23 00:00"
END_TIME = "2021-09-25 18:00"


def calculate_haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c


def generate_real_grid(output_path="data/processed/real_grid.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    rows = []
    half_grid = GRID_DIM // 2

    for c in PILOT_CITIES:
        c_lat, c_lon = c["lat"], c["lon"]
        c_id = c["city_id"]
        c_name = c["name"]

        for r in range(GRID_DIM):
            for col in range(GRID_DIM):
                row_idx = r - half_grid
                col_idx = col - half_grid

                lat = round(c_lat + row_idx * GRID_SPACING, 4)
                lon = round(c_lon + col_idx * GRID_SPACING, 4)
                grid_id = f"{c_id}_r{r}_c{col}"
                is_center = (r == half_grid and col == half_grid)

                rows.append({
                    "grid_id": grid_id,
                    "city_id": c_id,
                    "city_name": c_name,
                    "row": r,
                    "column": col,
                    "latitude": lat,
                    "longitude": lon,
                    "is_city_center": is_center,
                    "data_label": DATA_LABEL
                })

    df_grid = pd.DataFrame(rows)
    df_grid.to_csv(output_path, index=False)
    print(f"[Data Extraction] Created real grid: {output_path} ({len(df_grid)} cells)")
    return df_grid


def map_stations_to_grid(grid_df,
                          station_meta_path="data/real/openaq/station_metadata.csv",
                          output_path="data/processed/station_to_grid_mapping.csv"):
    station_df = pd.read_csv(station_meta_path)
    city_names = [c["name"] for c in PILOT_CITIES]
    sub_stations = station_df[station_df["city"].isin(city_names)].copy()

    mapping_records = []
    for _, st in sub_stations.iterrows():
        s_id = st["station_id"]
        s_name = st["station_name"]
        s_city = st["city"]
        s_lat = st["latitude"]
        s_lon = st["longitude"]

        # Match to cells of the same city
        c_cells = grid_df[grid_df["city_name"] == s_city]
        dists = calculate_haversine_km(s_lat, s_lon, c_cells["latitude"].values, c_cells["longitude"].values)
        min_idx = np.argmin(dists)
        nearest_cell = c_cells.iloc[min_idx]

        mapping_records.append({
            "station_id": s_id,
            "station_name": s_name,
            "city_name": s_city,
            "station_latitude": s_lat,
            "station_longitude": s_lon,
            "matched_grid_id": nearest_cell["grid_id"],
            "grid_latitude": nearest_cell["latitude"],
            "grid_longitude": nearest_cell["longitude"],
            "distance_km": round(float(dists[min_idx]), 2),
            "is_city_center": nearest_cell["is_city_center"]
        })

    df_map = pd.DataFrame(mapping_records)
    df_map.to_csv(output_path, index=False)
    print(f"[Data Extraction] Saved station-to-grid mapping: {output_path} ({len(df_map)} stations mapped)")
    return df_map


def extract_era5_winds(grid_df,
                       era5_raw_path="data/raw/era5/2021/era5_2021_instant.nc",
                       nc_out_path="data/real/era5/era5_u10_v10_pilot.nc",
                       csv_out_path="data/real/era5/era5_wind.csv"):
    os.makedirs(os.path.dirname(nc_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(csv_out_path), exist_ok=True)

    print(f"[ERA5 Extraction] Opening raw ERA5 dataset: {era5_raw_path}")
    ds = xr.open_dataset(era5_raw_path)
    t_coord = "valid_time" if "valid_time" in ds.coords else "time"

    # Slice time
    times = pd.date_range(START_TIME, END_TIME, freq="6h")
    ds_slice = ds[["u10", "v10"]].sel({t_coord: slice(START_TIME, END_TIME)})

    # Sliced geographical bounding box (covering pilot cities with generous buffer for transport)
    # Latitude descending: 32.0 to 22.0
    # Longitude ascending: 71.0 to 85.0
    ds_sub = ds_slice.sel(latitude=slice(32.0, 22.0), longitude=slice(71.0, 85.0))
    ds_sub.to_netcdf(nc_out_path)
    print(f"[ERA5 Extraction] Saved pilot NetCDF: {nc_out_path} ({round(os.path.getsize(nc_out_path)/(1024*1024), 2)} MB)")

    # Interpolate u10, v10 to grid coordinates
    wind_records = []
    for t_idx, t in enumerate(times):
        ds_t = ds_sub.sel({t_coord: t})
        t_str = pd.to_datetime(t).strftime("%Y-%m-%d %H:%M:%S UTC")

        for _, g in grid_df.iterrows():
            g_lat = g["latitude"]
            g_lon = g["longitude"]

            # Bilinear interpolation of u10 and v10
            pt = ds_t.interp(latitude=g_lat, longitude=g_lon, method="linear")
            u = float(pt["u10"].values)
            v = float(pt["v10"].values)

            w_speed = float(np.sqrt(u**2 + v**2))
            # Meteorological direction (direction wind blows FROM)
            # 270 - atan2(v, u) in degrees
            w_dir = float((270.0 - np.degrees(np.arctan2(v, u))) % 360.0)

            wind_records.append({
                "timestamp_utc": t_str,
                "timestamp_hour": t_idx * 6,
                "grid_id": g["grid_id"],
                "city_id": g["city_id"],
                "latitude": g_lat,
                "longitude": g_lon,
                "u10": round(u, 3),
                "v10": round(v, 3),
                "wind_speed": round(w_speed, 3),
                "wind_direction_deg": round(w_dir, 1),
                "data_label": DATA_LABEL
            })

    df_wind = pd.DataFrame(wind_records)
    df_wind.to_csv(csv_out_path, index=False)
    print(f"[ERA5 Extraction] Saved real ERA5 wind CSV: {csv_out_path} ({len(df_wind)} records)")
    ds.close()
    return df_wind


def aggregate_openaq_to_grid(grid_df,
                             station_map_df,
                             obs_path="data/real/openaq/pm25_observations.csv",
                             output_path="data/processed/openaq_pm25_grid.csv"):
    obs_df = pd.read_csv(obs_path)
    obs_df["dt"] = pd.to_datetime(obs_df["timestamp_utc"]).dt.tz_localize(None)

    # Filter to pilot time window
    times = pd.date_range(START_TIME, END_TIME, freq="6h")
    sub_obs = obs_df[(obs_df["dt"] >= START_TIME) & (obs_df["dt"] <= END_TIME)].copy()

    # Merge observation with station mapping
    merged_obs = sub_obs.merge(
        station_map_df[["station_id", "matched_grid_id", "city_name"]],
        on="station_id",
        how="inner"
    )

    pollution_records = []

    for t_idx, t in enumerate(times):
        t_str = pd.to_datetime(t).strftime("%Y-%m-%d %H:%M:%S UTC")
        # Match observations within +/- 1 hour window of the synoptic timestamp
        t_lower = t - pd.Timedelta(hours=1)
        t_upper = t + pd.Timedelta(hours=1)
        t_window = merged_obs[(merged_obs["dt"] >= t_lower) & (merged_obs["dt"] <= t_upper)]

        # Group by matched grid cell and city
        grid_pm25 = t_window.groupby(["matched_grid_id", "city_name"])["pm25"].agg(["mean", "count"]).reset_index()
        city_pm25 = t_window.groupby("city_name")["pm25"].mean().to_dict()

        for _, g in grid_df.iterrows():
            gid = g["grid_id"]
            c_name = g["city_name"]
            c_id = g["city_id"]

            match = grid_pm25[grid_pm25["matched_grid_id"] == gid]
            if not match.empty:
                val = round(float(match.iloc[0]["mean"]), 2)
                st_count = int(match.iloc[0]["count"])
            else:
                # If cell has no station, use city ambient mean as source baseline
                val = round(float(city_pm25.get(c_name, 25.0)), 2)
                st_count = 0

            pollution_records.append({
                "timestamp_utc": t_str,
                "timestamp_hour": t_idx * 6,
                "grid_id": gid,
                "city_id": c_id,
                "city_name": c_name,
                "latitude": g["latitude"],
                "longitude": g["longitude"],
                "pm25_concentration": val,
                "station_sample_count": st_count,
                "is_monitored_cell": (st_count > 0),
                "data_label": DATA_LABEL
            })

    df_pol = pd.DataFrame(pollution_records)
    df_pol.to_csv(output_path, index=False)
    print(f"[OpenAQ Ingestion] Saved real PM2.5 grid CSV: {output_path} ({len(df_pol)} records)")
    return df_pol


def align_wind_and_pollution(wind_df,
                             pol_df,
                             output_path="data/processed/openaq_era5_aligned.csv"):
    aligned = pd.merge(
        pol_df,
        wind_df[["timestamp_utc", "grid_id", "u10", "v10", "wind_speed", "wind_direction_deg"]],
        on=["timestamp_utc", "grid_id"],
        how="inner"
    )
    aligned.to_csv(output_path, index=False)
    print(f"[Alignment] Saved synchronized real dataset: {output_path} ({len(aligned)} records)")
    return aligned


def run_extraction_and_alignment():
    print("=" * 70)
    print("STARTING REAL ERA5 EXTRACTION & OPENAQ PM2.5 ALIGNMENT")
    print("=" * 70)

    grid_df = generate_real_grid()
    map_df = map_stations_to_grid(grid_df)
    wind_df = extract_era5_winds(grid_df)
    pol_df = aggregate_openaq_to_grid(grid_df, map_df)
    aligned_df = align_wind_and_pollution(wind_df, pol_df)

    print("=" * 70)
    print("EXTRACTION & ALIGNMENT COMPLETE!")
    print(f"Summary:")
    print(f"- Grid cells: {len(grid_df)} (5 cities x 49 cells)")
    print(f"- Mapped stations: {len(map_df)}")
    print(f"- Timestamps: {len(wind_df['timestamp_utc'].unique())} (6-hourly synoptic intervals)")
    print(f"- Aligned records: {len(aligned_df)}")
    print("=" * 70)


if __name__ == "__main__":
    run_extraction_and_alignment()
