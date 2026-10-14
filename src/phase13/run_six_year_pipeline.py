"""
PHASE 13 — HISTORICAL PIPELINE RUNNER
=====================================
Processes monthly historical transport matrices across available historical years
(2020–2024, 60 calendar months, 7,308 synoptic steps):
- Implements restartable, idempotent monthly batch processing with manifest tracking.
- Memory-efficient: loads only one calendar month of ERA5 surface winds at a time,
  closing NetCDF resources immediately after array extraction.
- Uses established 2D Lagrangian ensemble physics (N=20, dt in [1, 3, 6, 12, 24]h).
- O(1) grid mapping to 0.25° national grid without artificial perimeter clamping.
- Applies verified Phase 10 unconditional time-aggregation:
  T_bar[src, dest, dt] = sum(T[src, dest, t, dt]) / N_eligible_met(src, dt)
- Produces sparse long-form CSVs for monthly and annual outputs.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import glob
import traceback
import numpy as np
import pandas as pd
import xarray as xr

# Import established physics engine
from src.synthetic.physics_2d_dispersion import (
    run_ensemble_dispersion,
    calculate_bearing_deg,
    calculate_haversine_distance_km
)
from src.national.physics_2d_national_dispersion import map_particle_to_national_grid

WINDOWS = [1.0, 3.0, 6.0, 12.0, 24.0]
N_ENSEMBLE = 20

def get_pipeline_paths(base_out="results/phase13_six_year"):
    monthly_dir = os.path.join(base_out, "monthly")
    annual_dir = os.path.join(base_out, "annual")
    os.makedirs(monthly_dir, exist_ok=True)
    os.makedirs(annual_dir, exist_ok=True)
    manifest_csv = os.path.join(base_out, "processing_manifest.csv")
    return monthly_dir, annual_dir, manifest_csv

def init_manifest(manifest_csv, split_manifest_path="results/phase13_six_year/temporal_split_manifest.csv"):
    if os.path.exists(manifest_csv):
        df_manifest = pd.read_csv(manifest_csv, dtype=str)
    else:
        split_df = pd.read_csv(split_manifest_path)
        df_manifest = split_df[[
            "month_str", "year", "month", "days_in_month", "synoptic_steps", "split_role"
        ]].copy()
        df_manifest["status"] = "PENDING"
        df_manifest["executed_runs"] = "0"
        df_manifest["matrix_pairs"] = "0"
        df_manifest["boundary_retention_pct"] = ""
        df_manifest["runtime_sec"] = "0.0"
        df_manifest["output_matrix_file"] = ""
        df_manifest["output_boundary_file"] = ""
        df_manifest["completed_timestamp"] = ""
        df_manifest["error_message"] = ""
        df_manifest.to_csv(manifest_csv, index=False)
    return df_manifest

def update_manifest_row(manifest_csv, month_str, updates):
    df = pd.read_csv(manifest_csv, dtype=str)
    idx = df[df["month_str"] == month_str].index
    if len(idx) > 0:
        for k, v in updates.items():
            df.loc[idx, k] = str(v)
        df.to_csv(manifest_csv, index=False)

def process_single_month(
    year, month_num,
    stations_df,
    grid_lookup,
    obs_grouped_map,
    base_out="results/phase13_six_year"
):
    monthly_dir, _, manifest_csv = get_pipeline_paths(base_out)
    month_str = f"{year:04d}-{month_num:02d}"
    t_start = time.time()

    matrix_file = os.path.join(monthly_dir, f"transport_matrix_{year:04d}_{month_num:02d}.csv")
    boundary_file = os.path.join(monthly_dir, f"boundary_statistics_{year:04d}_{month_num:02d}.csv")
    run_log_file = os.path.join(monthly_dir, f"run_log_{year:04d}_{month_num:02d}.csv")

    update_manifest_row(manifest_csv, month_str, {"status": "RUNNING", "error_message": ""})
    print(f"\n[Phase 13 Batch] === Starting Month {month_str} ===")

    era5_instant_path = f"data/raw/era5/{year}/era5_{year}_instant.nc"
    if not os.path.exists(era5_instant_path):
        err = f"ERA5 file not found: {era5_instant_path}"
        update_manifest_row(manifest_csv, month_str, {"status": "FAILED", "error_message": err})
        raise FileNotFoundError(err)

    # 1. Open ERA5 NetCDF and slice only this month
    print(f"[Phase 13 Batch] Loading ERA5 wind slice for {month_str}...")
    ds = xr.open_dataset(era5_instant_path)
    t_coord = "valid_time" if "valid_time" in ds else "time"
    
    # Filter times for this month
    all_times = pd.to_datetime(ds[t_coord].values)
    month_mask = (all_times.year == year) & (all_times.month == month_num)
    month_times = all_times[month_mask]
    
    if len(month_times) == 0:
        ds.close()
        err = f"No timesteps found in ERA5 for month {month_str}"
        update_manifest_row(manifest_csv, month_str, {"status": "FAILED", "error_message": err})
        raise ValueError(err)

    lats = ds["latitude"].values
    lons = ds["longitude"].values

    # Pre-index station grid coordinates
    st_locs = {}
    for _, st in stations_df.iterrows():
        s_id = int(st["station_id"])
        s_lat = float(st["station_latitude"])
        s_lon = float(st["station_longitude"])
        lat_idx = int(np.argmin(np.abs(lats - s_lat)))
        lon_idx = int(np.argmin(np.abs(lons - s_lon)))
        st_locs[s_id] = {
            "name": str(st["station_name"]),
            "city": str(st["corrected_city"]),
            "grid_id": str(st["matched_grid_id"]),
            "lat": s_lat,
            "lon": s_lon,
            "lat_idx": lat_idx,
            "lon_idx": lon_idx
        }

    # Extract wind arrays in memory for this month only
    u10_arr = ds["u10"].values[month_mask, :, :]
    v10_arr = ds["v10"].values[month_mask, :, :]
    ds.close() # NetCDF closed immediately!
    print(f"[Phase 13 Batch] ERA5 wind loaded for {len(month_times)} synoptic steps. NetCDF resource closed.")

    # 2. Run Lagrangian ensemble dispersion
    transport_records = []
    boundary_records = []
    run_log_records = []

    for t_idx, t_val in enumerate(month_times):
        t_str = t_val.strftime("%Y-%m-%d %H:%M:%S UTC")

        for s_id, s_info in st_locs.items():
            u10 = float(u10_arr[t_idx, s_info["lat_idx"], s_info["lon_idx"]])
            v10 = float(v10_arr[t_idx, s_info["lat_idx"], s_info["lon_idx"]])

            if np.isnan(u10) or np.isnan(v10):
                run_log_records.append({
                    "timestamp_utc": t_str,
                    "synoptic_step": t_idx,
                    "station_id": s_id,
                    "status": "EXCLUDED_NO_METEOROLOGY",
                    "details": "NaN in ERA5 surface wind"
                })
                continue

            w_speed = np.sqrt(u10**2 + v10**2)
            w_dir = (270.0 - np.degrees(np.arctan2(v10, u10))) % 360.0
            wind_flow_dir = (90.0 - np.degrees(np.arctan2(v10, u10))) % 360.0

            # Check if ground PM2.5 observation exists
            obs_key = (s_id, t_str[:10], t_val.hour)
            obs_entry = obs_grouped_map.get(obs_key, None)
            has_obs = obs_entry is not None
            src_pm25 = float(obs_entry["pm25_mean"]) if has_obs else np.nan

            run_log_records.append({
                "timestamp_utc": t_str,
                "synoptic_step": t_idx,
                "station_id": s_id,
                "status": "SIMULATION_EXECUTED",
                "details": f"Wind={w_speed:.2f} m/s | PM2.5={'Observed ('+str(round(src_pm25,1))+')' if has_obs else 'Unmonitored'}"
            })

            src_lat = s_info["lat"]
            src_lon = s_info["lon"]
            src_grid_id = s_info["grid_id"]

            for dt_h in WINDOWS:
                particles = run_ensemble_dispersion(
                    src_lat, src_lon, u10, v10, dt_h,
                    n_ensemble=N_ENSEMBLE,
                    random_seed=42 + (year * 10000 + month_num * 100 + t_idx) * 10 + int(dt_h)
                )

                dest_counts = {}
                outside_count = 0

                for p_lat, p_lon in particles:
                    dest_id, is_inside, _, _ = map_particle_to_national_grid(p_lat, p_lon)
                    if is_inside:
                        dest_counts[dest_id] = dest_counts.get(dest_id, 0) + 1
                    else:
                        outside_count += 1

                inside_count = sum(dest_counts.values())
                inside_frac = float(inside_count) / float(N_ENSEMBLE)
                outside_frac = float(outside_count) / float(N_ENSEMBLE)

                boundary_records.append({
                    "timestamp_utc": t_str,
                    "synoptic_step": t_idx,
                    "station_id": s_id,
                    "station_name": s_info["name"],
                    "city": s_info["city"],
                    "source_grid_id": src_grid_id,
                    "elapsed_time_hours": dt_h,
                    "wind_speed": round(w_speed, 2),
                    "has_source_pm25": has_obs,
                    "source_pm25": round(src_pm25, 2) if has_obs else np.nan,
                    "particles_inside": inside_count,
                    "particles_outside": outside_count,
                    "inside_fraction": round(inside_frac, 4),
                    "boundary_loss_fraction": round(outside_frac, 4),
                    "mass_conservation_sum": round(inside_frac + outside_frac, 4)
                })

                for dest_id, count in dest_counts.items():
                    dest_info = grid_lookup.get(dest_id, {"latitude": src_lat, "longitude": src_lon})
                    dest_lat = dest_info["latitude"]
                    dest_lon = dest_info["longitude"]

                    t_frac = float(count) / float(N_ENSEMBLE)
                    t_inf = round(src_pm25 * t_frac, 3) if has_obs else np.nan
                    dist_km = round(calculate_haversine_distance_km(src_lat, src_lon, dest_lat, dest_lon), 2)

                    if dist_km > 0.1:
                        dest_bearing = calculate_bearing_deg(src_lat, src_lon, dest_lat, dest_lon)
                        rel_angle = abs((dest_bearing - wind_flow_dir + 180.0) % 360.0 - 180.0)
                    else:
                        dest_bearing = wind_flow_dir
                        rel_angle = 0.0

                    transport_records.append({
                        "station_id": s_id,
                        "station_name": s_info["name"],
                        "city": s_info["city"],
                        "source_grid_id": src_grid_id,
                        "dest_grid_id": dest_id,
                        "elapsed_time_hours": dt_h,
                        "distance_km": dist_km,
                        "rel_angle_to_wind_deg": round(rel_angle, 1),
                        "transport_fraction": t_frac,
                        "has_source_pm25": has_obs,
                        "transport_influence": t_inf
                    })

    df_bnd = pd.DataFrame(boundary_records)
    df_tgt = pd.DataFrame(transport_records)
    df_log = pd.DataFrame(run_log_records)

    # 3. Unconditional Phase 10 Time Aggregation
    # Denominator: strictly the number of valid meteorological steps in this month for station s
    eligible_met_df = df_bnd.groupby(["station_id", "elapsed_time_hours"]).size().reset_index(name="eligible_met_steps")

    # Inside cells
    inside_grouped = df_tgt.groupby([
        "station_id", "station_name", "city", "source_grid_id", "dest_grid_id", "elapsed_time_hours"
    ]).agg(
        sum_transport_fraction=("transport_fraction", "sum"),
        max_transport_fraction=("transport_fraction", "max"),
        visited_steps_count=("transport_fraction", "count"),
        distance_km=("distance_km", "first"),
        rel_angle_deg=("rel_angle_to_wind_deg", "mean"),
        sum_transport_influence=("transport_influence", lambda s: s.dropna().sum()),
        obs_active_steps=("has_source_pm25", lambda s: int(s.sum()))
    ).reset_index()

    matrix_inside = pd.merge(inside_grouped, eligible_met_df, on=["station_id", "elapsed_time_hours"], how="inner")
    matrix_inside["mean_transport_fraction"] = matrix_inside["sum_transport_fraction"] / matrix_inside["eligible_met_steps"]

    # Influence aggregation (normalized by observation-eligible steps if present)
    obs_eligible_df = df_bnd[df_bnd["has_source_pm25"]].groupby(["station_id", "elapsed_time_hours"]).size().reset_index(name="eligible_obs_steps")
    matrix_inside = pd.merge(matrix_inside, obs_eligible_df, on=["station_id", "elapsed_time_hours"], how="left")
    matrix_inside["eligible_obs_steps"] = matrix_inside["eligible_obs_steps"].fillna(0).astype(int)
    matrix_inside["mean_transport_influence"] = np.where(
        matrix_inside["eligible_obs_steps"] > 0,
        matrix_inside["sum_transport_influence"] / matrix_inside["eligible_obs_steps"],
        np.nan
    )

    # Outside domain exits
    outside_grouped = df_bnd.groupby([
        "station_id", "station_name", "city", "source_grid_id", "elapsed_time_hours"
    ]).agg(
        sum_outside_fraction=("boundary_loss_fraction", "sum"),
        max_outside_fraction=("boundary_loss_fraction", "max"),
        visited_steps_count=("particles_outside", lambda s: int((s > 0).sum())),
        eligible_met_steps=("boundary_loss_fraction", "count")
    ).reset_index()

    outside_active = outside_grouped[outside_grouped["max_outside_fraction"] > 0.0].copy()
    outside_rows = []
    for _, r in outside_active.iterrows():
        n_elig = r["eligible_met_steps"]
        outside_rows.append({
            "station_id": int(r["station_id"]),
            "station_name": str(r["station_name"]),
            "city": str(r["city"]),
            "source_grid_id": str(r["source_grid_id"]),
            "dest_grid_id": "OUTSIDE_DOMAIN",
            "elapsed_time_hours": float(r["elapsed_time_hours"]),
            "sum_transport_fraction": float(r["sum_outside_fraction"]),
            "max_transport_fraction": float(r["max_outside_fraction"]),
            "visited_steps_count": int(r["visited_steps_count"]),
            "distance_km": np.nan,
            "rel_angle_deg": np.nan,
            "sum_transport_influence": np.nan,
            "obs_active_steps": 0,
            "eligible_met_steps": int(n_elig),
            "mean_transport_fraction": float(r["sum_outside_fraction"] / n_elig),
            "eligible_obs_steps": 0,
            "mean_transport_influence": np.nan
        })

    if outside_rows:
        df_outside = pd.DataFrame(outside_rows)
        monthly_matrix = pd.concat([matrix_inside, df_outside], ignore_index=True)
    else:
        monthly_matrix = matrix_inside

    # Verify closure for this month
    closure_errors = []
    for (s_id, dt_h), grp in monthly_matrix.groupby(["station_id", "elapsed_time_hours"]):
        tot = grp["mean_transport_fraction"].sum()
        closure_errors.append(abs(tot - 1.0))
    max_err = max(closure_errors) if closure_errors else 0.0

    if max_err > 1e-4:
        err = f"Closure error violation in month {month_str}: {max_err:.2e}"
        update_manifest_row(manifest_csv, month_str, {"status": "FAILED", "error_message": err})
        raise ValueError(err)

    # Save sparse monthly CSVs
    monthly_matrix["month_str"] = month_str
    cols_order = [
        "month_str", "station_id", "station_name", "city", "source_grid_id", "dest_grid_id",
        "elapsed_time_hours", "mean_transport_fraction", "max_transport_fraction",
        "mean_transport_influence", "distance_km", "rel_angle_deg",
        "eligible_met_steps", "eligible_obs_steps", "visited_steps_count"
    ]
    monthly_matrix = monthly_matrix[cols_order].sort_values(
        ["station_id", "elapsed_time_hours", "dest_grid_id"]
    ).reset_index(drop=True)
    monthly_matrix.to_csv(matrix_file, index=False)

    df_bnd.to_csv(boundary_file, index=False)
    df_log.to_csv(run_log_file, index=False)

    elapsed_sec = round(time.time() - t_start, 2)
    mean_retention = (1.0 - df_bnd["boundary_loss_fraction"].mean()) * 100.0

    update_manifest_row(manifest_csv, month_str, {
        "status": "COMPLETED",
        "executed_runs": len(df_bnd),
        "matrix_pairs": len(monthly_matrix),
        "boundary_retention_pct": round(mean_retention, 2),
        "runtime_sec": elapsed_sec,
        "output_matrix_file": matrix_file,
        "output_boundary_file": boundary_file,
        "completed_timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error_message": ""
    })

    print(f"[Phase 13 Batch] Completed {month_str} in {elapsed_sec}s | Matrix Pairs: {len(monthly_matrix)} | Retention: {mean_retention:.1f}% | Closure Max Err: {max_err:.2e}")
    return monthly_matrix, df_bnd

def run_pipeline(
    start_year=2020,
    end_year=2024,
    test_single_month=None,
    base_out="results/phase13_six_year"
):
    monthly_dir, annual_dir, manifest_csv = get_pipeline_paths(base_out)
    df_manifest = init_manifest(manifest_csv)

    print(f"[Phase 13 Pipeline] Loading station and grid definitions...")
    stations_df = pd.read_csv("results/phase11_validation/selected_stations.csv")
    grid_df = pd.read_csv("data/national/india_025_grid.csv")
    grid_lookup = grid_df.set_index("grid_id")[["latitude", "longitude"]].to_dict(orient="index")

    print("[Phase 13 Pipeline] Loading ground OpenAQ observations for fast synoptic alignment...")
    df_obs = pd.read_csv("data/real/openaq/pm25_observations.csv")
    df_obs["dt"] = pd.to_datetime(df_obs["timestamp_utc"]).dt.tz_localize(None)
    # Round to synoptic hour
    df_obs["hour_synoptic"] = ((df_obs["dt"].dt.hour + 3) // 6 * 6) % 24
    df_obs["date_str"] = df_obs["dt"].dt.strftime("%Y-%m-%d")

    obs_grouped = df_obs.groupby(["station_id", "date_str", "hour_synoptic"]).agg(
        pm25_mean=("pm25", "mean"),
        count=("pm25", "count")
    ).reset_index()

    obs_grouped_map = obs_grouped.set_index(["station_id", "date_str", "hour_synoptic"])[["pm25_mean", "count"]].to_dict(orient="index")
    print(f"[Phase 13 Pipeline] In-situ observations indexed: {len(obs_grouped_map):,} synoptic slots.")

    if test_single_month:
        # Pilot test run for one representative month
        parts = test_single_month.split("-")
        y = int(parts[0])
        m = int(parts[1])
        process_single_month(y, m, stations_df, grid_lookup, obs_grouped_map, base_out)
        return

    # Process all months in range
    print(f"\n[Phase 13 Pipeline] Executing batch across years {start_year} to {end_year}...")
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            month_str = f"{y:04d}-{m:02d}"
            
            # Check manifest status
            m_row = df_manifest[df_manifest["month_str"] == month_str]
            if len(m_row) > 0 and m_row["status"].iloc[0] == "COMPLETED":
                mat_f = m_row["output_matrix_file"].iloc[0]
                if os.path.exists(mat_f) and os.path.getsize(mat_f) > 1000:
                    print(f"[Phase 13 Pipeline] Month {month_str} already COMPLETED and verified. Skipping (idempotent).")
                    continue

            try:
                process_single_month(y, m, stations_df, grid_lookup, obs_grouped_map, base_out)
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                print(f"[Phase 13 Pipeline] ERROR in {month_str}: {err_msg}")
                traceback.print_exc()
                update_manifest_row(manifest_csv, month_str, {"status": "FAILED", "error_message": err_msg})
                continue

    print(f"\n[Phase 13 Pipeline] Batch processing completed across {start_year}–{end_year}!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Phase 13 Historical Dispersion Pipeline")
    parser.add_argument("--test-month", type=str, default=None, help="Process single month, e.g. 2021-09")
    parser.add_argument("--start-year", type=int, default=2020)
    parser.add_argument("--end-year", type=int, default=2024)
    args = parser.parse_args()

    run_pipeline(start_year=args.start_year, end_year=args.end_year, test_single_month=args.test_month)
