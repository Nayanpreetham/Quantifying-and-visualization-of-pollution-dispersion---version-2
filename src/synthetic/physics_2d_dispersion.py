"""
2D PHYSICS & ENSEMBLE DISPERSION MODEL
=====================================
Calculates synthetic 2D physics-based grid-to-grid advection and ensemble dispersion.

Inputs:
- data/synthetic/grid.csv
- data/synthetic/pollution.csv
- data/synthetic/era5_wind.csv

Outputs:
- data/synthetic/transport_targets.csv
- results/physics/physics_dispersion_summary.csv
- results/physics/ensemble_stability_benchmark.csv

Mathematical & Physical Concepts:
- 2D Kinematic Advection: dx = U * dt, dy = V * dt
- Ensemble Dispersion: Particle spread via Gaussian wind vector perturbations (N=20 default)
- Grid-to-Grid Mapping: Direct regular lat/lon indexing
- Transport Matrix T[src, dest, t]: Normalized fraction of particles advected from src to dest cell
- Transported Pollution Influence: PM2.5_src * T[src, dest, t]
"""

import os
import numpy as np
import pandas as pd

DISCLAIMER = "SYNTHETIC DATA — PIPELINE/CONSTRAINT VERIFICATION ONLY"


def calculate_bearing_deg(lat1, lon1, lat2, lon2):
    """Calculate compass bearing in degrees from point 1 to point 2."""
    dlon = np.radians(lon2 - lon1)
    lat1_r, lat2_r = np.radians(lat1), np.radians(lat2)

    y = np.sin(dlon) * np.cos(lat2_r)
    x = np.cos(lat1_r) * np.sin(lat2_r) - np.sin(lat1_r) * np.cos(lat2_r) * np.cos(dlon)

    bearing = np.degrees(np.arctan2(y, x))
    return (bearing + 360.0) % 360.0


def calculate_haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculate Haversine distance in kilometers between two lat/lon points."""
    R = 6371.0  # Earth radius in km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)

    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c


def run_ensemble_dispersion(src_lat, src_lon, u10, v10, elapsed_hours, n_ensemble=20, random_seed=42):
    """
    Simulates N 2D advection trajectories with stochastic dispersion.

    Parameters:
    - src_lat, src_lon: Source grid center coordinates
    - u10, v10: Horizontal wind components (m/s)
    - elapsed_hours: Time window (hours)
    - n_ensemble: Number of ensemble members

    Returns:
    - List of (dest_lat, dest_lon) for all N particles
    """
    rng = np.random.RandomState(random_seed)
    dt_sec = elapsed_hours * 3600.0

    base_speed = np.sqrt(u10**2 + v10**2)
    base_angle_rad = np.arctan2(v10, u10)

    particle_destinations = []

    for i in range(n_ensemble):
        if i == 0:
            # Deterministic central trajectory member
            u_p, v_p = u10, v10
        else:
            # Stochastic ensemble perturbation (speed jitter & directional spread)
            speed_pert = base_speed + rng.normal(0, 0.4)
            speed_pert = max(0.2, speed_pert)

            angle_pert = base_angle_rad + rng.normal(0, np.radians(12.0))

            u_p = speed_pert * np.cos(angle_pert)
            v_p = speed_pert * np.sin(angle_pert)

        # Displacement in meters
        dx_m = u_p * dt_sec
        dy_m = v_p * dt_sec

        # Convert meters to degrees latitude & longitude
        dlat = dy_m / 111000.0
        dlon = dx_m / (111000.0 * np.cos(np.radians(src_lat)))

        p_lat = src_lat + dlat
        p_lon = src_lon + dlon
        particle_destinations.append((p_lat, p_lon))

    return particle_destinations


def map_particle_to_grid(lat, lon, city_grid_df):
    """
    Direct regular grid lookup: maps continuous lat/lon to nearest cell in city grid.
    """
    # Calculate distance to all cells in the city grid
    dists = np.sqrt((city_grid_df["latitude"].values - lat)**2 + (city_grid_df["longitude"].values - lon)**2)
    min_idx = np.argmin(dists)
    return city_grid_df.iloc[min_idx]["grid_id"]


def generate_transport_targets(data_dir="data/synthetic", results_dir="results/physics", n_ensemble=20):
    os.makedirs(results_dir, exist_ok=True)

    grid_path = os.path.join(data_dir, "grid.csv")
    pol_path = os.path.join(data_dir, "pollution.csv")
    wind_path = os.path.join(data_dir, "era5_wind.csv")

    grid_df = pd.read_csv(grid_path)
    pol_df = pd.read_csv(pol_path)
    wind_df = pd.read_csv(wind_path)

    # Filter to city centers as primary source grid candidates
    center_grids = grid_df[grid_df["is_city_center"] == True]

    records = []
    elapsed_time_windows = [1.0, 3.0, 6.0]  # Hours

    for _, src_row in center_grids.iterrows():
        c_id = src_row["city_id"]
        c_name = src_row["city_name"]
        src_id = src_row["grid_id"]
        src_lat = src_row["latitude"]
        src_lon = src_row["longitude"]

        city_cells = grid_df[grid_df["city_id"] == c_id].copy()

        # Select a few representative timestamps (e.g. Hour 0, 3, 6, 9)
        sample_hours = [0, 3, 6, 9]

        for h in sample_hours:
            # Fetch wind and pollution
            w_sub = wind_df[(wind_df["grid_id"] == src_id) & (wind_df["timestamp_hour"] == h)]
            p_sub = pol_df[(pol_df["grid_id"] == src_id) & (pol_df["timestamp_hour"] == h)]

            if w_sub.empty or p_sub.empty:
                continue

            u10 = w_sub.iloc[0]["u10"]
            v10 = w_sub.iloc[0]["v10"]
            w_speed = w_sub.iloc[0]["wind_speed"]
            w_dir = w_sub.iloc[0]["wind_direction_deg"]
            src_pm25 = p_sub.iloc[0]["pm25_concentration"]

            for dt_h in elapsed_time_windows:
                particles = run_ensemble_dispersion(src_lat, src_lon, u10, v10, dt_h, n_ensemble=n_ensemble)

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
                    transport_influence = round(src_pm25 * transport_fraction, 3)

                    rel_dx = round(dest_lon - src_lon, 4)
                    rel_dy = round(dest_lat - src_lat, 4)
                    dist_km = round(calculate_haversine_distance_km(src_lat, src_lon, dest_lat, dest_lon), 2)

                    # Vector direction where wind blows TO (0° = North, 90° = East)
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
                        "timestamp_hour": h,
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
                        "data_label": DISCLAIMER
                    })

    df_out = pd.DataFrame(records)
    target_path = os.path.join(data_dir, "transport_targets.csv")
    df_out.to_csv(target_path, index=False)
    print(f"[Physics 2D Model] Saved transport targets: {target_path} ({len(df_out)} target pairs)")

    # Save summary report
    summary_path = os.path.join(results_dir, "physics_dispersion_summary.csv")
    summary = df_out.groupby(["city_name", "elapsed_time_hours"]).agg(
        active_dest_cells=("transport_fraction", lambda x: (x > 0).sum()),
        max_transport_influence=("transport_influence", "max"),
        mean_transport_influence=("transport_influence", "mean"),
        total_conserved_fraction=("transport_fraction", "sum")
    ).reset_index()
    summary.to_csv(summary_path, index=False)
    print(f"[Physics 2D Model] Saved physics summary: {summary_path}")

    return df_out


def benchmark_ensemble_stability(data_dir="data/synthetic", results_dir="results/physics"):
    """
    Tests ensemble stability for N = 5, 10, 20.
    Measures rank correlation and MAE of transport fraction as N increases.
    """
    print("[Physics 2D Model] Benchmarking ensemble stability (N=5, 10, 20)...")
    grid_df = pd.read_csv(os.path.join(data_dir, "grid.csv"))

    # Test Delhi center
    del_center = grid_df[grid_df["grid_id"] == "DEL_r3_c3"].iloc[0]
    city_cells = grid_df[grid_df["city_id"] == "DEL"].copy()

    src_lat, src_lon = del_center["latitude"], del_center["longitude"]
    u10, v10 = 3.5, -2.0  # NW wind
    dt_h = 3.0

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

    # Compare N=5 vs N=20 and N=10 vs N=20
    mae_5_20 = float(np.mean(np.abs(results[5] - results[20])))
    mae_10_20 = float(np.mean(np.abs(results[10] - results[20])))

    stab_df = pd.DataFrame([
        {"ensemble_comparison": "N=5 vs N=20", "mae_fraction_diff": round(mae_5_20, 4), "stability_status": "PASS" if mae_5_20 < 0.10 else "FAIL"},
        {"ensemble_comparison": "N=10 vs N=20", "mae_fraction_diff": round(mae_10_20, 4), "stability_status": "PASS" if mae_10_20 < 0.05 else "FAIL"},
    ])

    stab_path = os.path.join(results_dir, "ensemble_stability_benchmark.csv")
    stab_df.to_csv(stab_path, index=False)
    print(f"[Physics 2D Model] Saved ensemble stability benchmark: {stab_path}")
    return stab_df


if __name__ == "__main__":
    generate_transport_targets()
    benchmark_ensemble_stability()
