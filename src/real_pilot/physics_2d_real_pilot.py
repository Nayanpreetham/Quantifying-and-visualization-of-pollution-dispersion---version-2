"""
REAL DATA 2D PHYSICS & ENSEMBLE DISPERSION PILOT
================================================
Step 4 & Step 5 of Real Data Pipeline:
- Reuses the verified 2D kinematic advection & ensemble dispersion physics engine
  from src/synthetic/physics_2d_dispersion.py
- Takes real OpenAQ PM2.5 observations and real ERA5 U10/V10 surface winds
- Computes Source -> Destination Grid Transport Matrix T[src, dest, t]
- Calculates Transported Pollution Influence = PM2.5_src * T[src, dest, t]
- Distinguishes modelled transport influence from local ambient concentration

Inputs:
- data/processed/real_grid.csv
- data/processed/openaq_era5_aligned.csv

Outputs:
- results/real_pilot/transport_targets.csv
- results/real_pilot/transport_matrix_summary.csv
- results/real_pilot/dispersion_summary.csv
- results/real_pilot/ensemble_stability_benchmark.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd

from src.synthetic.physics_2d_dispersion import (
    run_ensemble_dispersion,
    map_particle_to_grid,
    calculate_bearing_deg,
    calculate_haversine_distance_km
)

DATA_LABEL = "REAL DATA — OPENAQ OBSERVATIONS & ERA5 REANALYSIS"


def run_real_dispersion_pilot(grid_path="data/processed/real_grid.csv",
                              aligned_path="data/processed/openaq_era5_aligned.csv",
                              results_dir="results/real_pilot",
                              n_ensemble=20):
    os.makedirs(results_dir, exist_ok=True)

    grid_df = pd.read_csv(grid_path)
    aligned_df = pd.read_csv(aligned_path)

    # City center grids as primary monitored source grids
    center_grids = grid_df[grid_df["is_city_center"] == True]

    records = []
    elapsed_time_windows = [1.0, 3.0, 6.0]  # Hours

    timestamps = aligned_df["timestamp_utc"].unique()
    print(f"[Real Pilot] Processing {len(center_grids)} pilot cities across {len(timestamps)} synoptic timestamps...")

    for _, src_row in center_grids.iterrows():
        c_id = src_row["city_id"]
        c_name = src_row["city_name"]
        src_id = src_row["grid_id"]
        src_lat = src_row["latitude"]
        src_lon = src_row["longitude"]

        city_cells = grid_df[grid_df["city_id"] == c_id].copy()

        for t_str in timestamps:
            sub = aligned_df[(aligned_df["grid_id"] == src_id) & (aligned_df["timestamp_utc"] == t_str)]
            if sub.empty:
                continue

            row = sub.iloc[0]
            u10 = row["u10"]
            v10 = row["v10"]
            w_speed = row["wind_speed"]
            w_dir = row["wind_direction_deg"]
            src_pm25 = row["pm25_concentration"]
            t_hour = int(row["timestamp_hour"])

            for dt_h in elapsed_time_windows:
                particles = run_ensemble_dispersion(
                    src_lat, src_lon, u10, v10, dt_h, n_ensemble=n_ensemble, random_seed=42 + t_hour
                )

                # Count particle arrivals per destination cell
                dest_counts = {}
                for p_lat, p_lon in particles:
                    dest_id = map_particle_to_grid(p_lat, p_lon, city_cells)
                    dest_counts[dest_id] = dest_counts.get(dest_id, 0) + 1

                # Generate records for all destination cells in the city grid
                for _, dest_row in city_cells.iterrows():
                    dest_id = dest_row["grid_id"]
                    dest_lat = dest_row["latitude"]
                    dest_lon = dest_row["longitude"]

                    count = dest_counts.get(dest_id, 0)
                    transport_fraction = float(count) / float(n_ensemble)
                    # Modelled transport influence: src_pm25 * T[src, dest, t]
                    transport_influence = round(src_pm25 * transport_fraction, 3)

                    rel_dx = round(dest_lon - src_lon, 4)
                    rel_dy = round(dest_lat - src_lat, 4)
                    dist_km = round(calculate_haversine_distance_km(src_lat, src_lon, dest_lat, dest_lon), 2)

                    # Vector flow direction where wind blows TO (0 = North, 90 = East)
                    wind_flow_dir = (90.0 - np.degrees(np.arctan2(v10, u10))) % 360.0

                    if dist_km > 0.1:
                        dest_bearing = calculate_bearing_deg(src_lat, src_lon, dest_lat, dest_lon)
                        rel_angle = abs((dest_bearing - wind_flow_dir + 180.0) % 360.0 - 180.0)
                    else:
                        dest_bearing = wind_flow_dir
                        rel_angle = 0.0

                    records.append({
                        "city_id": c_id,
                        "city_name": c_name,
                        "timestamp_utc": t_str,
                        "timestamp_hour": t_hour,
                        "elapsed_time_hours": dt_h,
                        "source_grid_id": src_id,
                        "dest_grid_id": dest_id,
                        "source_lat": src_lat,
                        "source_lon": src_lon,
                        "dest_lat": dest_lat,
                        "dest_lon": dest_lon,
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
                        "transport_fraction": round(transport_fraction, 4),
                        "transport_influence": transport_influence,
                        "data_label": DATA_LABEL
                    })

    df_out = pd.DataFrame(records)
    target_path = os.path.join(results_dir, "transport_targets.csv")
    df_out.to_csv(target_path, index=False)
    print(f"[Real Pilot] Saved transport targets: {target_path} ({len(df_out)} target pairs)")

    # 1. Transport Matrix Summary (Source -> Dest mean fractions and influence)
    matrix_path = os.path.join(results_dir, "transport_matrix_summary.csv")
    matrix_df = df_out.groupby(["city_name", "source_grid_id", "dest_grid_id", "elapsed_time_hours"]).agg(
        mean_transport_fraction=("transport_fraction", "mean"),
        max_transport_fraction=("transport_fraction", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        max_transport_influence=("transport_influence", "max"),
        distance_km=("distance_km", "first"),
        rel_angle_deg=("rel_angle_to_wind_deg", "mean")
    ).reset_index()
    matrix_df.to_csv(matrix_path, index=False)
    print(f"[Real Pilot] Saved transport matrix summary: {matrix_path} ({len(matrix_df)} pairs)")

    # 2. General Dispersion Summary per City and dt
    disp_path = os.path.join(results_dir, "dispersion_summary.csv")
    disp_summary = df_out.groupby(["city_name", "elapsed_time_hours"]).agg(
        active_dest_cells=("transport_fraction", lambda x: (x > 0).sum()),
        mean_source_pm25=("source_pm25", "mean"),
        max_transport_influence=("transport_influence", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        mean_transport_fraction=("transport_fraction", "mean"),
        total_conserved_fraction=("transport_fraction", "sum")
    ).reset_index()
    disp_summary.to_csv(disp_path, index=False)
    print(f"[Real Pilot] Saved dispersion summary: {disp_path}")

    return df_out


def benchmark_real_ensemble_stability(grid_path="data/processed/real_grid.csv",
                                       aligned_path="data/processed/openaq_era5_aligned.csv",
                                       results_dir="results/real_pilot"):
    """
    Tests ensemble stability for N = 5, 10, 20 on real wind vectors.
    """
    print("[Real Pilot] Benchmarking ensemble stability (N=5, 10, 20) with real ERA5 winds...")
    grid_df = pd.read_csv(grid_path)
    aligned_df = pd.read_csv(aligned_path)

    # Test Kanpur center at 2021-09-23 06:00 UTC (strong wind: speed 4.65 m/s)
    test_rows = aligned_df[(aligned_df["city_id"] == "KNP") & (aligned_df["is_monitored_cell"] == True)]
    sample = test_rows.iloc[0]

    src_lat, src_lon = sample["latitude"], sample["longitude"]
    u10, v10 = sample["u10"], sample["v10"]
    dt_h = 3.0
    city_cells = grid_df[grid_df["city_id"] == "KNP"].copy()

    n_sizes = [5, 10, 20]
    results = {}

    for n in n_sizes:
        particles = run_ensemble_dispersion(src_lat, src_lon, u10, v10, dt_h, n_ensemble=n, random_seed=42)
        counts = {}
        for p_lat, p_lon in particles:
            dest_id = map_particle_to_grid(p_lat, p_lon, city_cells)
            counts[dest_id] = counts.get(dest_id, 0) + 1

        fractions = np.array([counts.get(gid, 0) / float(n) for gid in city_cells["grid_id"]])
        results[n] = fractions

    mae_5_20 = float(np.mean(np.abs(results[5] - results[20])))
    mae_10_20 = float(np.mean(np.abs(results[10] - results[20])))

    stab_df = pd.DataFrame([
        {"ensemble_comparison": "N=5 vs N=20", "mae_fraction_diff": round(mae_5_20, 4), "stability_status": "PASS" if mae_5_20 < 0.10 else "FAIL"},
        {"ensemble_comparison": "N=10 vs N=20", "mae_fraction_diff": round(mae_10_20, 4), "stability_status": "PASS" if mae_10_20 < 0.05 else "FAIL"},
    ])

    stab_path = os.path.join(results_dir, "ensemble_stability_benchmark.csv")
    stab_df.to_csv(stab_path, index=False)
    print(f"[Real Pilot] Saved real ensemble stability benchmark: {stab_path}")
    return stab_df


if __name__ == "__main__":
    run_real_dispersion_pilot()
    benchmark_real_ensemble_stability()
