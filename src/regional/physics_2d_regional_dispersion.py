"""
2D REGIONAL PHYSICS & ENSEMBLE DISPERSION ENGINE (CONTINUOUS IGP GRID)
=====================================================================
Phase 6: Executes the 2D Lagrangian ensemble dispersion model on the continuous
0.25° x 0.25° Indo-Gangetic Plain regional grid:
- Reuses established 2D advection equations & Gaussian perturbation ensemble (N=20).
- Uses continuous regular grid (1,881 cells) across 24°N–32°N and 74°E–88°E.
- Zero edge clamping: particles moving beyond domain bounds are explicitly tracked
  as OUTSIDE_DOMAIN with boundary-loss statistics.
- Computes Source -> Destination Transport Matrix T[src, dest, t] and
  Transported Pollution Influence I = PM2.5_src * T[src, dest, t].

Inputs:
- data/regional/igp_025_grid.csv
- data/regional/openaq_era5_aligned_regional.csv

Outputs:
- results/regional_pilot/transport_targets_regional.csv
- results/regional_pilot/transport_matrix_regional.csv
- results/regional_pilot/boundary_loss_statistics.csv
- results/regional_pilot/regional_dispersion_summary.csv
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

DATA_LABEL = "REGIONAL DATA — CONTINUOUS IGP 0.25° GRID"

LAT_MAX = 32.0
LAT_MIN = 24.0
LON_MIN = 74.0
LON_MAX = 88.0
GRID_RES = 0.25
N_ROWS = int(round((LAT_MAX - LAT_MIN) / GRID_RES)) + 1  # 33
N_COLS = int(round((LON_MAX - LON_MIN) / GRID_RES)) + 1  # 57


def map_particle_to_continuous_grid(lat, lon):
    """
    O(1) continuous regular grid lookup.
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
        return f"IGP_r{r:02d}_c{c:02d}", True, r, c
    else:
        return "OUTSIDE_DOMAIN", False, None, None


def run_regional_dispersion(grid_path="data/regional/igp_025_grid.csv",
                            aligned_path="data/regional/openaq_era5_aligned_regional.csv",
                            results_dir="results/regional_pilot",
                            n_ensemble=20):
    os.makedirs(results_dir, exist_ok=True)

    grid_df = pd.read_csv(grid_path)
    aligned_df = pd.read_csv(aligned_path)

    # Key regional corridor stations
    source_stations = aligned_df["station_id"].unique()
    print(f"[Regional Physics] Processing {len(source_stations)} source stations across {len(aligned_df['timestamp_utc'].unique())} synoptic time steps...")

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
                dest_id, is_inside, _, _ = map_particle_to_continuous_grid(p_lat, p_lon)
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
                "ensemble_n": n_ensemble,
                "particles_inside": inside_count,
                "particles_outside": outside_count,
                "inside_fraction": round(inside_fraction, 4),
                "boundary_loss_fraction": round(boundary_loss_fraction, 4),
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
    target_path = os.path.join(results_dir, "transport_targets_regional.csv")
    df_out.to_csv(target_path, index=False)
    print(f"[Regional Physics] Saved regional transport targets: {target_path} ({len(df_out)} active transport pairs)")

    df_bnd = pd.DataFrame(boundary_stats)
    bnd_path = os.path.join(results_dir, "boundary_loss_statistics.csv")
    df_bnd.to_csv(bnd_path, index=False)
    print(f"[Regional Physics] Saved boundary loss statistics: {bnd_path} ({len(df_bnd)} runs)")

    # Aggregated Transport Matrix T[src, dest, dt]
    matrix_df = df_out.groupby(["station_id", "station_name", "city", "source_grid_id", "dest_grid_id", "elapsed_time_hours"]).agg(
        mean_transport_fraction=("transport_fraction", "mean"),
        max_transport_fraction=("transport_fraction", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        max_transport_influence=("transport_influence", "max"),
        distance_km=("distance_km", "first"),
        rel_angle_deg=("rel_angle_to_wind_deg", "mean")
    ).reset_index()
    matrix_path = os.path.join(results_dir, "transport_matrix_regional.csv")
    matrix_df.to_csv(matrix_path, index=False)
    print(f"[Regional Physics] Saved aggregated transport matrix: {matrix_path} ({len(matrix_df)} matrix pairs)")

    # Regional dispersion summary
    summary = df_out.groupby(["city", "elapsed_time_hours"]).agg(
        active_dest_cells=("dest_grid_id", "nunique"),
        mean_source_pm25=("source_pm25", "mean"),
        max_transport_influence=("transport_influence", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        mean_distance_km=("distance_km", "mean"),
        max_distance_km=("distance_km", "max")
    ).reset_index()
    summary_path = os.path.join(results_dir, "regional_dispersion_summary.csv")
    summary.to_csv(summary_path, index=False)
    print(f"[Regional Physics] Saved regional dispersion summary: {summary_path}")

    return df_out, df_bnd


if __name__ == "__main__":
    run_regional_dispersion()
