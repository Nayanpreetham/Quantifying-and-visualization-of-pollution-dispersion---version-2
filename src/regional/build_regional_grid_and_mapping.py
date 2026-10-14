"""
REGIONAL GRID & STATION MAPPING ENGINE (INDO-GANGETIC PLAIN)
=============================================================
Phase 6: Builds the Continuous Regional 0.25° Grid and Corrects Station Mapping:
1. Generates 1,881 contiguous 0.25° x 0.25° grid cells covering the IGP corridor (24°N–32°N, 74°E–88°E)
   matching ERA5 grid coordinates 1:1.
2. Corrects station metadata (e.g. Prayagraj Station 227384 mislabeled as Agra).
3. Matches stations by geographic distance with an explicit 25.0 km threshold.
4. Rejects stations outside domain cleanly (no distant misattributions).
5. Extracts native ERA5 U10/V10 for October 14–20, 2021 (28 synoptic 6-hourly steps).
6. Ingests ground in-situ OpenAQ hourly PM2.5 observations for all active regional stations.

Outputs:
- data/regional/igp_025_grid.csv
- data/regional/station_to_grid_mapping_corrected.csv
- data/regional/era5_wind_regional.nc
- data/regional/era5_wind_regional.csv
- data/regional/openaq_pm25_regional_sources.csv
- data/regional/openaq_era5_aligned_regional.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd
import xarray as xr

DATA_LABEL = "REGIONAL DATA — OPENAQ OBSERVATIONS & ERA5 REANALYSIS (IGP)"

LAT_MIN = 24.0
LAT_MAX = 32.0
LON_MIN = 74.0
LON_MAX = 88.0
GRID_RES = 0.25
MAX_STATION_DISTANCE_KM = 25.0

START_TIME = "2021-10-14 00:00"
END_TIME = "2021-10-20 18:00"


def calculate_haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    return R * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


def build_continuous_regional_grid(output_path="data/regional/igp_025_grid.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # ERA5 coordinates: descending latitudes, ascending longitudes
    lats = np.arange(LAT_MAX, LAT_MIN - 0.001, -GRID_RES)
    lons = np.arange(LON_MIN, LON_MAX + 0.001, GRID_RES)

    grid_rows = []
    n_rows = len(lats)
    n_cols = len(lons)

    for r_idx, lat in enumerate(lats):
        for c_idx, lon in enumerate(lons):
            is_boundary = (r_idx == 0 or r_idx == n_rows - 1 or c_idx == 0 or c_idx == n_cols - 1)
            grid_id = f"IGP_r{r_idx:02d}_c{c_idx:02d}"
            grid_rows.append({
                "grid_id": grid_id,
                "row": r_idx,
                "column": c_idx,
                "latitude": round(float(lat), 4),
                "longitude": round(float(lon), 4),
                "is_boundary_cell": is_boundary,
                "domain": "Indo-Gangetic Plain",
                "resolution_deg": GRID_RES,
                "data_label": DATA_LABEL
            })

    grid_df = pd.DataFrame(grid_rows)
    grid_df.to_csv(output_path, index=False)
    print(f"[Regional Grid] Created continuous regional grid: {output_path} ({len(grid_df)} cells: {n_rows} rows x {n_cols} cols)")
    return grid_df


def map_stations_corrected(grid_df,
                           meta_path="data/real/openaq/station_metadata.csv",
                           output_path="data/regional/station_to_grid_mapping_corrected.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    meta = pd.read_csv(meta_path)

    mapping_records = []
    grid_lats = grid_df["latitude"].values
    grid_lons = grid_df["longitude"].values

    for _, st in meta.iterrows():
        s_id = int(st["station_id"])
        s_name = str(st["station_name"])
        s_city = str(st["city"])
        s_lat = float(st["latitude"])
        s_lon = float(st["longitude"])

        # Correct station metadata anomalies based on verifiable geographic facts
        if s_id == 227384 and ("Prayagraj" in s_name or "Jhunsi" in s_name):
            corrected_city = "Prayagraj"
            correction_note = "CORRECTED: Mislabeled upstream as Agra; coordinates (25.426N, 81.917E) place station in Prayagraj (Allahabad), UP."
        else:
            corrected_city = s_city
            correction_note = "Original city label retained"

        # Calculate pure geographic distance to all regional grid cells
        dists = calculate_haversine_km(s_lat, s_lon, grid_lats, grid_lons)
        min_idx = np.argmin(dists)
        min_dist = float(dists[min_idx])

        if min_dist <= MAX_STATION_DISTANCE_KM:
            nearest = grid_df.iloc[min_idx]
            mapping_records.append({
                "station_id": s_id,
                "station_name": s_name,
                "original_city": s_city,
                "corrected_city": corrected_city,
                "station_latitude": s_lat,
                "station_longitude": s_lon,
                "matched_grid_id": nearest["grid_id"],
                "grid_latitude": nearest["latitude"],
                "grid_longitude": nearest["longitude"],
                "distance_km": round(min_dist, 2),
                "match_status": "MATCHED",
                "audit_note": correction_note
            })
        else:
            mapping_records.append({
                "station_id": s_id,
                "station_name": s_name,
                "original_city": s_city,
                "corrected_city": corrected_city,
                "station_latitude": s_lat,
                "station_longitude": s_lon,
                "matched_grid_id": "UNMATCHED_OUTSIDE_DOMAIN",
                "grid_latitude": np.nan,
                "grid_longitude": np.nan,
                "distance_km": round(min_dist, 2),
                "match_status": "REJECTED_OUTSIDE_DOMAIN",
                "audit_note": f"Exceeds maximum threshold of {MAX_STATION_DISTANCE_KM} km (outside regional bounding box)"
            })

    map_df = pd.DataFrame(mapping_records)
    map_df.to_csv(output_path, index=False)
    matched_count = (map_df["match_status"] == "MATCHED").sum()
    rejected_count = (map_df["match_status"] == "REJECTED_OUTSIDE_DOMAIN").sum()
    print(f"[Station Mapping] Saved corrected station mapping: {output_path}")
    print(f"                 Matched in IGP: {matched_count} stations | Rejected outside domain: {rejected_count} stations")
    return map_df


def extract_regional_era5_winds(grid_df,
                                raw_nc_path="data/raw/era5/2021/era5_2021_instant.nc",
                                nc_out_path="data/regional/era5_wind_regional.nc",
                                csv_out_path="data/regional/era5_wind_regional.csv"):
    os.makedirs(os.path.dirname(nc_out_path), exist_ok=True)
    os.makedirs(os.path.dirname(csv_out_path), exist_ok=True)

    print(f"[ERA5 Regional] Opening raw ERA5 dataset: {raw_nc_path}")
    ds = xr.open_dataset(raw_nc_path)
    t_coord = "valid_time" if "valid_time" in ds.coords else "time"

    # Slice exact temporal and spatial window
    ds_slice = ds[["u10", "v10"]].sel({t_coord: slice(START_TIME, END_TIME)})
    ds_sub = ds_slice.sel(latitude=slice(LAT_MAX, LAT_MIN), longitude=slice(LON_MIN, LON_MAX))
    ds_sub.to_netcdf(nc_out_path)
    print(f"[ERA5 Regional] Saved regional NetCDF: {nc_out_path} ({round(os.path.getsize(nc_out_path)/(1024*1024), 2)} MB)")

    # Build tabular wind dataframe directly from 1:1 matching grid nodes
    wind_records = []
    times = ds_sub[t_coord].values

    for t_idx, t in enumerate(times):
        t_dt = pd.to_datetime(t)
        t_str = t_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        ds_t = ds_sub.sel({t_coord: t})

        u_grid = ds_t["u10"].values  # shape (33, 57)
        v_grid = ds_t["v10"].values  # shape (33, 57)

        for _, g in grid_df.iterrows():
            r = int(g["row"])
            c = int(g["column"])
            u = float(u_grid[r, c])
            v = float(v_grid[r, c])
            w_speed = float(np.sqrt(u**2 + v**2))
            w_dir = float((270.0 - np.degrees(np.arctan2(v, u))) % 360.0)

            wind_records.append({
                "timestamp_utc": t_str,
                "synoptic_step": t_idx,
                "grid_id": g["grid_id"],
                "row": r,
                "column": c,
                "latitude": g["latitude"],
                "longitude": g["longitude"],
                "u10": round(u, 3),
                "v10": round(v, 3),
                "wind_speed": round(w_speed, 3),
                "wind_direction_deg": round(w_dir, 1),
                "data_label": DATA_LABEL
            })

    df_wind = pd.DataFrame(wind_records)
    df_wind.to_csv(csv_out_path, index=False)
    print(f"[ERA5 Regional] Saved regional tabular winds: {csv_out_path} ({len(df_wind)} records: {len(times)} times x {len(grid_df)} cells)")
    ds.close()
    return df_wind


def ingest_regional_openaq(grid_df,
                           map_df,
                           obs_path="data/real/openaq/pm25_observations.csv",
                           output_path="data/regional/openaq_pm25_regional_sources.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    obs = pd.read_csv(obs_path)
    obs["dt"] = pd.to_datetime(obs["timestamp_utc"]).dt.tz_localize(None)

    # Filter to active stations matched in IGP
    matched_stations = map_df[map_df["match_status"] == "MATCHED"].copy()
    sub_obs = obs[obs["station_id"].isin(matched_stations["station_id"])].copy()
    sub_obs = sub_obs[(sub_obs["dt"] >= START_TIME) & (sub_obs["dt"] <= END_TIME)]

    merged = sub_obs.merge(
        matched_stations[["station_id", "matched_grid_id", "corrected_city"]],
        on="station_id",
        how="inner"
    )

    times = pd.date_range(START_TIME, END_TIME, freq="6h")
    records = []

    for t_idx, t in enumerate(times):
        t_str = pd.to_datetime(t).strftime("%Y-%m-%d %H:%M:%S UTC")
        t_low = t - pd.Timedelta(hours=1)
        t_high = t + pd.Timedelta(hours=1)
        t_window = merged[(merged["dt"] >= t_low) & (merged["dt"] <= t_high)]

        # Group by matched grid cell and station
        grouped = t_window.groupby(["matched_grid_id", "station_id", "station_name", "corrected_city"]).agg(
            pm25_mean=("pm25", "mean"),
            sample_count=("pm25", "count")
        ).reset_index()

        for _, row in grouped.iterrows():
            grid_info = grid_df[grid_df["grid_id"] == row["matched_grid_id"]].iloc[0]
            records.append({
                "timestamp_utc": t_str,
                "synoptic_step": t_idx,
                "grid_id": row["matched_grid_id"],
                "station_id": int(row["station_id"]),
                "station_name": row["station_name"],
                "city": row["corrected_city"],
                "grid_latitude": grid_info["latitude"],
                "grid_longitude": grid_info["longitude"],
                "pm25_concentration": round(float(row["pm25_mean"]), 2),
                "hourly_samples": int(row["sample_count"]),
                "is_source_grid": True,
                "data_label": DATA_LABEL
            })

    df_pol = pd.DataFrame(records)
    df_pol.to_csv(output_path, index=False)
    print(f"[OpenAQ Regional] Saved active regional source observations: {output_path} ({len(df_pol)} station-time records)")
    return df_pol


def align_regional_data(wind_df,
                         pol_df,
                         output_path="data/regional/openaq_era5_aligned_regional.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Merge source observations with the exact grid wind at each timestamp
    aligned = pd.merge(
        pol_df,
        wind_df[["timestamp_utc", "grid_id", "u10", "v10", "wind_speed", "wind_direction_deg"]],
        on=["timestamp_utc", "grid_id"],
        how="inner"
    )
    aligned.to_csv(output_path, index=False)
    print(f"[Regional Alignment] Saved aligned source dataset: {output_path} ({len(aligned)} records)")
    return aligned


def run_regional_prep():
    print("=" * 70)
    print("STARTING REGIONAL GRID CONSTRUCTION & DATA PREPARATION")
    print("=" * 70)
    grid_df = build_continuous_regional_grid()
    map_df = map_stations_corrected(grid_df)
    wind_df = extract_regional_era5_winds(grid_df)
    pol_df = ingest_regional_openaq(grid_df, map_df)
    aligned_df = align_regional_data(wind_df, pol_df)
    print("=" * 70)
    print("REGIONAL PREPARATION COMPLETE!")
    print("=" * 70)


if __name__ == "__main__":
    run_regional_prep()
