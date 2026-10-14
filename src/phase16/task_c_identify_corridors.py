"""
PHASE 16 — TASK C: RECURRING TRANSPORT CORRIDORS & PERSISTENCE
=============================================================
Identifies and characterizes recurring transport corridors across India:
1. Ranks top-5 destination grids per source station and advection window.
2. Measures corridor persistence across 72 monthly matrices and 6 annual matrices.
3. Classifies distance bands:
   - LOCAL_SELF (< 30 km)
   - NEAR_REGIONAL (30 to < 100 km)
   - REGIONAL (100 to < 250 km)
   - LONG_RANGE (>= 250 km)
   - DOMAIN_EXIT (OUTSIDE_DOMAIN)
4. Pre-defined threshold sensitivity: tau in [0.01, 0.02, 0.05, 0.10].
5. Uses exact primary key (station_id, dest_grid_id, elapsed_time_hours).
6. Outputs:
   - results/phase16_climatology/tables/top_transport_corridors.csv
   - results/phase16_climatology/tables/corridor_persistence.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd

from src.synthetic.physics_2d_dispersion import calculate_haversine_distance_km, calculate_bearing_deg
from src.phase16.task_a_audit_inputs import get_matrix_file_path

THRESHOLDS = [0.01, 0.02, 0.05, 0.10]
PRIMARY_TAU = 0.05

def classify_distance_band(dest_id, dist_km):
    if dest_id == "OUTSIDE_DOMAIN":
        return "DOMAIN_EXIT"
    elif np.isnan(dist_km) or dist_km < 30.0:
        return "LOCAL_SELF"
    elif dist_km < 100.0:
        return "NEAR_REGIONAL"
    elif dist_km < 250.0:
        return "REGIONAL"
    else:
        return "LONG_RANGE"

def identify_corridors(out_dir="results/phase16_climatology/tables"):
    os.makedirs(out_dir, exist_ok=True)
    top_corridors_csv = os.path.join(out_dir, "top_transport_corridors.csv")
    persistence_csv = os.path.join(out_dir, "corridor_persistence.csv")

    # Load 6-year master climatological baseline matrix
    master_clim_path = "results/phase16_climatology/matrices/transport_matrix_climatology_six_year_baseline.csv"
    df_clim = pd.read_csv(master_clim_path)

    # Load individual annual matrices indexed by (station_id, dest_grid_id, elapsed_time_hours)
    annual_matrices = {}
    for y in range(2019, 2025):
        fpath = f"results/phase16_climatology/matrices/transport_matrix_annual_{y}.csv"
        df_ann = pd.read_csv(fpath)
        annual_matrices[y] = df_ann.set_index(["station_id", "dest_grid_id", "elapsed_time_hours"])

    # Load monthly matrices to track monthly presence
    monthly_presence = {tau: {} for tau in THRESHOLDS}

    print("[Task C] Scanning all 72 monthly matrices for threshold sensitivity & monthly recurrence...")
    for y in range(2019, 2025):
        for m in range(1, 13):
            m_path = get_matrix_file_path(y, m)
            df_m = pd.read_csv(m_path)
            for s_id, d_gid, dt_h, frac in df_m[["station_id", "dest_grid_id", "elapsed_time_hours", "mean_transport_fraction"]].itertuples(index=False):
                key = (int(s_id), str(d_gid), float(dt_h))
                f_val = float(frac)
                for tau in THRESHOLDS:
                    if f_val >= tau:
                        monthly_presence[tau][key] = monthly_presence[tau].get(key, 0) + 1

    # 1. Top Corridors Ranking per Source Station and Window
    print("[Task C] Ranking top destination grids per station & advection window...")
    top_records = []
    
    for (s_id, dt_h), grp in df_clim.groupby(["station_id", "elapsed_time_hours"]):
        sorted_grp = grp.sort_values("mean_transport_fraction", ascending=False).reset_index(drop=True)
        top5 = sorted_grp.head(5)

        for rank, (_, row) in enumerate(top5.iterrows(), start=1):
            src_gid = row["source_grid_id"]
            d_gid = row["dest_grid_id"]
            d_km = float(row["distance_km"]) if not np.isnan(row["distance_km"]) else np.nan
            d_band = classify_distance_band(d_gid, d_km)
            mean_t = float(row["mean_transport_fraction"])
            key = (int(s_id), str(d_gid), float(dt_h))

            # Annual tracking: how many years was this corridor active at primary tau (0.05)?
            active_years = []
            annual_fracs = []
            for y in range(2019, 2025):
                ann_dict = annual_matrices[y]
                if key in ann_dict.index:
                    ann_t = float(ann_dict.loc[key, "mean_transport_fraction"])
                    annual_fracs.append(ann_t)
                    if ann_t >= PRIMARY_TAU:
                        active_years.append(y)
                else:
                    annual_fracs.append(0.0)

            n_years_active = len(active_years)
            n_months_active = monthly_presence[PRIMARY_TAU].get(key, 0)
            persistence_rate = n_years_active / 6.0

            top_records.append({
                "source_grid_id": src_gid,
                "station_id": int(s_id),
                "station_name": row["station_name"],
                "source_city": row["city"],
                "destination_grid_id": d_gid,
                "advection_window_hours": dt_h,
                "corridor_rank": rank,
                "climatological_mean_transport_fraction": round(mean_t, 5),
                "distance_km": round(d_km, 2) if not np.isnan(d_km) else np.nan,
                "bearing_deg": round(float(row["rel_angle_deg"]), 1) if not np.isnan(row["rel_angle_deg"]) else np.nan,
                "distance_band": d_band,
                "annual_recurrence_count_out_of_6": n_years_active,
                "annual_persistence_rate": round(persistence_rate, 4),
                "monthly_active_months_out_of_72": n_months_active,
                "monthly_persistence_rate": round(n_months_active / 72.0, 4),
                "annual_fractions_2019_2024": str([round(f, 4) for f in annual_fracs]),
                "persistence_category": (
                    "HIGHLY_PERSISTENT" if persistence_rate >= 0.8 else
                    ("MODERATELY_PERSISTENT" if persistence_rate >= 0.5 else "TRANSIENT")
                )
            })

    df_top = pd.DataFrame(top_records)
    df_top.to_csv(top_corridors_csv, index=False)
    print(f"[Task C] Saved top transport corridors: {top_corridors_csv} ({len(df_top)} corridors)")

    # 2. Comprehensive Corridor Persistence & Threshold Sensitivity
    print("[Task C] Compiling corridor persistence and threshold sensitivity analysis...")
    persistence_records = []

    for _, row in df_clim.iterrows():
        s_id = int(row["station_id"])
        src_gid = row["source_grid_id"]
        d_gid = row["dest_grid_id"]
        dt_h = float(row["elapsed_time_hours"])
        mean_t = float(row["mean_transport_fraction"])
        d_km = float(row["distance_km"]) if not np.isnan(row["distance_km"]) else np.nan
        d_band = classify_distance_band(d_gid, d_km)
        key = (s_id, str(d_gid), dt_h)

        years_active_by_tau = {}
        for tau in THRESHOLDS:
            y_cnt = 0
            for y in range(2019, 2025):
                ann_dict = annual_matrices[y]
                if key in ann_dict.index:
                    if float(ann_dict.loc[key, "mean_transport_fraction"]) >= tau:
                        y_cnt += 1
            years_active_by_tau[tau] = y_cnt

        persistence_records.append({
            "source_grid_id": src_gid,
            "station_id": s_id,
            "station_name": row["station_name"],
            "source_city": row["city"],
            "destination_grid_id": d_gid,
            "advection_window_hours": dt_h,
            "distance_km": round(d_km, 2) if not np.isnan(d_km) else np.nan,
            "distance_band": d_band,
            "climatological_transport_fraction": round(mean_t, 5),
            "years_active_tau_0_01": years_active_by_tau[0.01],
            "years_active_tau_0_02": years_active_by_tau[0.02],
            "years_active_tau_0_05": years_active_by_tau[0.05],
            "years_active_tau_0_10": years_active_by_tau[0.10],
            "months_active_tau_0_01": monthly_presence[0.01].get(key, 0),
            "months_active_tau_0_02": monthly_presence[0.02].get(key, 0),
            "months_active_tau_0_05": monthly_presence[0.05].get(key, 0),
            "months_active_tau_0_10": monthly_presence[0.10].get(key, 0),
            "primary_annual_persistence_rate": round(years_active_by_tau[PRIMARY_TAU] / 6.0, 4),
            "primary_monthly_persistence_rate": round(monthly_presence[PRIMARY_TAU].get(key, 0) / 72.0, 4),
            "persistence_classification": (
                "HIGHLY_PERSISTENT" if years_active_by_tau[PRIMARY_TAU] >= 5 else
                ("MODERATELY_PERSISTENT" if years_active_by_tau[PRIMARY_TAU] >= 3 else "TRANSIENT")
            )
        })

    df_pers = pd.DataFrame(persistence_records)
    df_pers.to_csv(persistence_csv, index=False)
    print(f"[Task C] Saved corridor persistence: {persistence_csv} ({len(df_pers)} total links)")

    print("\n=== THRESHOLD SENSITIVITY SUMMARY ===")
    for tau in THRESHOLDS:
        col = f"years_active_tau_{tau:.2f}".replace(".", "_")
        n_links = (df_pers[col] >= 3).sum()
        pct_persistent = (df_pers[col] >= 5).sum()
        print(f"Threshold tau = {tau:.2f}: {n_links:,} links recurring in >= 3 years | {pct_persistent:,} highly persistent (>= 5 years)")

    return df_top, df_pers

if __name__ == "__main__":
    identify_corridors()
