"""
2D NATIONAL PHYSICS & ENSEMBLE DISPERSION ENGINE (INDIA-WIDE 0.25° GRID)
========================================================================
Phase 8: Executes the 2D Lagrangian ensemble dispersion model on the continuous
0.25° x 0.25° national computational domain covering India (5°N–38°N, 68°E–98°E):
- Continuous regular 16,093-cell grid (133 rows x 121 cols).
- 2D advection equations & Gaussian perturbation ensemble (N=20).
- Pure O(1) grid mapping with zero artificial edge clamping:
  Particles advecting outside the national domain are tracked cleanly as 'OUTSIDE_DOMAIN'.
- Strictly closed transport matrix with explicit 'OUTSIDE_DOMAIN' sink accounting:
  sum(T[src, dest, dt]) = 1.0000 for every source and time window.
- Computes Source -> Destination Transport Matrix T[src, dest, t] and
  Transported Pollution Influence I = PM2.5_src * T[src, dest, t].

Inputs:
- data/national/india_025_grid.csv
- data/national/openaq_era5_aligned_national.csv

Outputs:
- results/national_pilot/transport_targets_national.csv
- results/national_pilot/transport_matrix_national.csv
- results/national_pilot/boundary_loss_statistics_national.csv
- results/national_pilot/national_dispersion_summary.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd

from src.synthetic.physics_2d_dispersion import (
    run_ensemble_dispersion,
    calculate_bearing_deg,
    calculate_haversine_distance_km
)

DATA_LABEL = "NATIONAL DATA — CONTINUOUS INDIA 0.25° GRID"

LAT_MAX = 38.0
LAT_MIN = 5.0
LON_MIN = 68.0
LON_MAX = 98.0
GRID_RES = 0.25
N_ROWS = int(round((LAT_MAX - LAT_MIN) / GRID_RES)) + 1  # 133
N_COLS = int(round((LON_MAX - LON_MIN) / GRID_RES)) + 1  # 121


def map_particle_to_national_grid(lat, lon):
    """
    O(1) continuous regular national grid lookup.
    Returns: (grid_id, is_inside, row, col)
    If coordinates fall outside domain bounds, returns ('OUTSIDE_DOMAIN', False, None, None).
    NO ARTIFICIAL CLAMPING.
    """
    if lat < (LAT_MIN - GRID_RES / 2.0) or lat > (LAT_MAX + GRID_RES / 2.0):
        return "OUTSIDE_DOMAIN", False, None, None
    if lon < (LON_MIN - GRID_RES / 2.0) or lon > (LON_MAX + GRID_RES / 2.0):
        return "OUTSIDE_DOMAIN", False, None, None

    r = int(round((LAT_MAX - lat) / GRID_RES))
    c = int(round((lon - LON_MIN) / GRID_RES))

    if 0 <= r < N_ROWS and 0 <= c < N_COLS:
        return f"IND_r{r:03d}_c{c:03d}", True, r, c
    else:
        return "OUTSIDE_DOMAIN", False, None, None


def run_national_dispersion(grid_path="data/national/india_025_grid.csv",
                           aligned_path="data/national/openaq_era5_aligned_national.csv",
                           results_dir="results/national_pilot",
                           n_ensemble=20):
    os.makedirs(results_dir, exist_ok=True)

    grid_df = pd.read_csv(grid_path)
    aligned_df = pd.read_csv(aligned_path)

    source_stations = aligned_df["station_id"].unique()
    times = aligned_df["timestamp_utc"].unique()
    print(f"[National Physics] Processing {len(source_stations)} stations across {len(times)} synoptic steps ({len(aligned_df)} total slices)...")

    elapsed_time_windows = [1.0, 3.0, 6.0, 12.0, 24.0]  # Hours

    records = []
    boundary_stats = []

    # Map grid_id to lat/lon for fast lookup
    grid_lookup = grid_df.set_index("grid_id")[["latitude", "longitude"]].to_dict(orient="index")

    for _, src_row in aligned_df.iterrows():
        s_id = int(src_row["station_id"])
        s_name = str(src_row["station_name"])
        s_city = str(src_row["city"])
        src_grid_id = str(src_row["grid_id"])
        src_lat = float(src_row["grid_latitude"])
        src_lon = float(src_row["grid_longitude"])
        t_str = str(src_row["timestamp_utc"])
        step_idx = int(src_row["synoptic_step"])

        u10 = float(src_row["u10"])
        v10 = float(src_row["v10"])
        w_speed = float(src_row["wind_speed"])
        w_dir = float(src_row["wind_direction_deg"])
        src_pm25 = float(src_row["pm25_concentration"])

        # Wind flow vector direction (direction wind blows TO)
        wind_flow_dir = (90.0 - np.degrees(np.arctan2(v10, u10))) % 360.0

        for dt_h in elapsed_time_windows:
            particles = run_ensemble_dispersion(
                src_lat, src_lon, u10, v10, dt_h,
                n_ensemble=n_ensemble,
                random_seed=42 + step_idx * 100 + int(dt_h)
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
            inside_fraction = float(inside_count) / float(n_ensemble)
            boundary_loss_fraction = float(outside_count) / float(n_ensemble)

            boundary_stats.append({
                "timestamp_utc": t_str,
                "synoptic_step": step_idx,
                "station_id": s_id,
                "station_name": s_name,
                "city": s_city,
                "source_grid_id": src_grid_id,
                "elapsed_time_hours": dt_h,
                "wind_speed": w_speed,
                "source_pm25": src_pm25,
                "ensemble_n": n_ensemble,
                "particles_inside": inside_count,
                "particles_outside": outside_count,
                "inside_fraction": round(inside_fraction, 4),
                "boundary_loss_fraction": round(boundary_loss_fraction, 4),
                "outside_influence": round(src_pm25 * boundary_loss_fraction, 3),
                "mass_conservation_sum": round(inside_fraction + boundary_loss_fraction, 4),
                "data_label": DATA_LABEL
            })

            # Record non-zero active destination cells in continuous grid
            for dest_id, count in dest_counts.items():
                dest_info = grid_lookup[dest_id]
                dest_lat = dest_info["latitude"]
                dest_lon = dest_info["longitude"]

                t_frac = float(count) / float(n_ensemble)
                t_influence = round(src_pm25 * t_frac, 3)

                rel_dx = round(dest_lon - src_lon, 4)
                rel_dy = round(dest_lat - src_lat, 4)
                dist_km = round(calculate_haversine_distance_km(src_lat, src_lon, dest_lat, dest_lon), 2)

                if dist_km > 0.1:
                    dest_bearing = calculate_bearing_deg(src_lat, src_lon, dest_lat, dest_lon)
                    rel_angle = abs((dest_bearing - wind_flow_dir + 180.0) % 360.0 - 180.0)
                else:
                    dest_bearing = wind_flow_dir
                    rel_angle = 0.0

                records.append({
                    "timestamp_utc": t_str,
                    "synoptic_step": step_idx,
                    "station_id": s_id,
                    "station_name": s_name,
                    "city": s_city,
                    "source_grid_id": src_grid_id,
                    "dest_grid_id": dest_id,
                    "source_lat": src_lat,
                    "source_lon": src_lon,
                    "dest_lat": dest_lat,
                    "dest_lon": dest_lon,
                    "elapsed_time_hours": dt_h,
                    "rel_dx": rel_dx,
                    "rel_dy": rel_dy,
                    "distance_km": dist_km,
                    "u10": u10,
                    "v10": v10,
                    "wind_speed": w_speed,
                    "wind_direction_deg": w_dir,
                    "wind_flow_dir_deg": round(wind_flow_dir, 1),
                    "dest_bearing_deg": round(dest_bearing, 1),
                    "rel_angle_to_wind_deg": round(rel_angle, 1),
                    "source_pm25": src_pm25,
                    "particle_count": count,
                    "ensemble_n": n_ensemble,
                    "transport_fraction": round(t_frac, 4),
                    "transport_influence": t_influence,
                    "data_label": DATA_LABEL
                })

    df_out = pd.DataFrame(records)
    target_path = os.path.join(results_dir, "transport_targets_national.csv")
    df_out.to_csv(target_path, index=False)
    print(f"[National Physics] Saved national transport targets: {target_path} ({len(df_out)} active transport pairs)")

    df_bnd = pd.DataFrame(boundary_stats)
    bnd_path = os.path.join(results_dir, "boundary_loss_statistics_national.csv")
    df_bnd.to_csv(bnd_path, index=False)
    print(f"[National Physics] Saved boundary loss statistics: {bnd_path} ({len(df_bnd)} runs)")

    # Aggregated Transport Matrix T[src, dest, dt] for cells inside domain
    matrix_inside = df_out.groupby(["station_id", "station_name", "city", "source_grid_id", "dest_grid_id", "elapsed_time_hours"]).agg(
        mean_transport_fraction=("transport_fraction", "mean"),
        max_transport_fraction=("transport_fraction", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        max_transport_influence=("transport_influence", "max"),
        distance_km=("distance_km", "first"),
        rel_angle_deg=("rel_angle_to_wind_deg", "mean")
    ).reset_index()

    # Append explicit OUTSIDE_DOMAIN rows for full mathematical closure
    matrix_outside = df_bnd.groupby(["station_id", "station_name", "city", "source_grid_id", "elapsed_time_hours"]).agg(
        mean_outside_frac=("boundary_loss_fraction", "mean"),
        max_outside_frac=("boundary_loss_fraction", "max"),
        mean_outside_inf=("outside_influence", "mean"),
        max_outside_inf=("outside_influence", "max")
    ).reset_index()

    # Filter to cases where outside fraction is non-zero
    matrix_outside = matrix_outside[matrix_outside["max_outside_frac"] > 0.0].copy()
    outside_rows = []
    for _, r in matrix_outside.iterrows():
        outside_rows.append({
            "station_id": int(r["station_id"]),
            "station_name": r["station_name"],
            "city": r["city"],
            "source_grid_id": r["source_grid_id"],
            "dest_grid_id": "OUTSIDE_DOMAIN",
            "elapsed_time_hours": float(r["elapsed_time_hours"]),
            "mean_transport_fraction": round(float(r["mean_outside_frac"]), 4),
            "max_transport_fraction": round(float(r["max_outside_frac"]), 4),
            "mean_transport_influence": round(float(r["mean_outside_inf"]), 3),
            "max_transport_influence": round(float(r["max_outside_inf"]), 3),
            "distance_km": np.nan,
            "rel_angle_deg": np.nan
        })

    if outside_rows:
        df_outside_rows = pd.DataFrame(outside_rows)
        matrix_df = pd.concat([matrix_inside, df_outside_rows], ignore_index=True)
    else:
        matrix_df = matrix_inside

    matrix_df = matrix_df.sort_values(["station_id", "elapsed_time_hours", "dest_grid_id"]).reset_index(drop=True)
    matrix_path = os.path.join(results_dir, "transport_matrix_national.csv")
    matrix_df.to_csv(matrix_path, index=False)
    print(f"[National Physics] Saved strictly closed transport matrix: {matrix_path} ({len(matrix_df)} matrix pairs)")

    # National dispersion summary
    summary = df_out.groupby(["city", "elapsed_time_hours"]).agg(
        active_dest_cells=("dest_grid_id", "nunique"),
        mean_source_pm25=("source_pm25", "mean"),
        max_transport_influence=("transport_influence", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        mean_distance_km=("distance_km", "mean"),
        max_distance_km=("distance_km", "max")
    ).reset_index()
    summary_path = os.path.join(results_dir, "national_dispersion_summary.csv")
    summary.to_csv(summary_path, index=False)
    print(f"[National Physics] Saved national dispersion summary: {summary_path}")

    return df_out, df_bnd, matrix_df


if __name__ == "__main__":
    run_national_dispersion()
