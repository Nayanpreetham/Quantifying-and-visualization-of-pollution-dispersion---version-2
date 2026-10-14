"""
PHASE 16 — TASK B: SEASONAL & ANNUAL MATRIX AGGREGATION
======================================================
Constructs step-weighted seasonal and multi-year climatological transport matrices:
- Unconditional step-weighted pooling derived from Phase 10:
    T_season[src, dest, dt] = sum_m (T_m[src, dest, dt] * N_met_m) / sum_m (N_met_m)
- Exactly preserves probability closure (sum_d T_season = 1.0) without distortion.
- Defined seasons:
    * Winter: Dec–Feb (DJF) - evaluated both cross-year (DJF) and within-year (JF + D)
    * Pre-monsoon: Mar–May (MAM)
    * Monsoon: Jun–Sep (JJAS)
    * Post-monsoon: Oct–Nov (ON)
- Produces:
    * 24 Individual seasonal matrices (4 seasons x 6 years)
    * 4 Climatological 6-year seasonal matrices (Winter, Pre-monsoon, Monsoon, Post-monsoon)
    * 1 Full six-year climatological baseline matrix (2019–2024, 72 months)
    * results/phase16_climatology/tables/seasonal_transport_summary.csv
    * results/phase16_climatology/tables/annual_transport_summary.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd

from src.phase16.task_a_audit_inputs import get_matrix_file_path

WINDOWS = [1.0, 3.0, 6.0, 12.0, 24.0]

SEASONS_DEF = {
    "Winter": [12, 1, 2],
    "Pre-monsoon": [3, 4, 5],
    "Monsoon": [6, 7, 8, 9],
    "Post-monsoon": [10, 11]
}

def aggregate_monthly_subset(month_tuples, period_label):
    """
    month_tuples: list of (year, month_num)
    Returns aggregated matrix DataFrame, verifying closure.
    """
    dfs = []
    total_eligible_steps_by_station = {}

    for (y, m) in month_tuples:
        fpath = get_matrix_file_path(y, m)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Missing monthly matrix: {fpath}")
        df_m = pd.read_csv(fpath)
        dfs.append(df_m)

    all_df = pd.concat(dfs, ignore_index=True)

    # Step-weighted pooling
    all_df["weighted_frac"] = all_df["mean_transport_fraction"] * all_df["eligible_met_steps"]
    all_df["weighted_infl"] = np.where(
        all_df["mean_transport_influence"].notna(),
        all_df["mean_transport_influence"] * all_df["eligible_obs_steps"],
        0.0
    )

    # Group by link
    grp_cols = ["station_id", "station_name", "city", "source_grid_id", "dest_grid_id", "elapsed_time_hours"]
    agg_df = all_df.groupby(grp_cols).agg(
        sum_weighted_frac=("weighted_frac", "sum"),
        max_transport_fraction=("max_transport_fraction", "max"),
        sum_weighted_infl=("weighted_infl", "sum"),
        distance_km=("distance_km", "first"),
        rel_angle_deg=("rel_angle_deg", "mean"),
        visited_steps_count=("visited_steps_count", "sum")
    ).reset_index()

    # Calculate total eligible steps per station-window
    elig_steps = all_df.groupby(["station_id", "elapsed_time_hours", "month_str"]).agg(
        met_steps=("eligible_met_steps", "first"),
        obs_steps=("eligible_obs_steps", "first")
    ).reset_index()

    station_totals = elig_steps.groupby(["station_id", "elapsed_time_hours"]).agg(
        period_eligible_met_steps=("met_steps", "sum"),
        period_eligible_obs_steps=("obs_steps", "sum")
    ).reset_index()

    merged = pd.merge(agg_df, station_totals, on=["station_id", "elapsed_time_hours"], how="inner")
    merged["mean_transport_fraction"] = merged["sum_weighted_frac"] / merged["period_eligible_met_steps"]
    merged["mean_transport_influence"] = np.where(
        merged["period_eligible_obs_steps"] > 0,
        merged["sum_weighted_infl"] / merged["period_eligible_obs_steps"],
        np.nan
    )

    merged["period_label"] = period_label

    cols_order = [
        "period_label", "station_id", "station_name", "city", "source_grid_id", "dest_grid_id",
        "elapsed_time_hours", "mean_transport_fraction", "max_transport_fraction",
        "mean_transport_influence", "distance_km", "rel_angle_deg",
        "period_eligible_met_steps", "period_eligible_obs_steps", "visited_steps_count"
    ]
    res_df = merged[cols_order].sort_values(["station_id", "elapsed_time_hours", "dest_grid_id"]).reset_index(drop=True)

    # Check closure
    closure = res_df.groupby(["station_id", "elapsed_time_hours"])["mean_transport_fraction"].sum()
    max_err = float((closure - 1.0).abs().max())
    assert max_err < 1e-4, f"Closure violation in {period_label}: max error {max_err:.2e}"

    return res_df, max_err

def run_seasonal_and_annual_aggregation(out_dir="results/phase16_climatology/tables"):
    os.makedirs(out_dir, exist_ok=True)
    seasonal_summary_csv = os.path.join(out_dir, "seasonal_transport_summary.csv")
    annual_summary_csv = os.path.join(out_dir, "annual_transport_summary.csv")
    matrices_dir = os.path.join("results/phase16_climatology", "matrices")
    os.makedirs(matrices_dir, exist_ok=True)

    print("[Task B] 1. Generating Annual Transport Summaries (2019–2024)...")
    annual_records = []
    annual_dfs = {}

    for y in range(2019, 2025):
        m_tuples = [(y, m) for m in range(1, 13)]
        ann_df, max_err = aggregate_monthly_subset(m_tuples, f"{y}-ANNUAL")
        ann_out_path = os.path.join(matrices_dir, f"transport_matrix_annual_{y}.csv")
        ann_df.to_csv(ann_out_path, index=False)
        annual_dfs[y] = ann_df

        # Metrics
        ann_inside = ann_df[ann_df["dest_grid_id"] != "OUTSIDE_DOMAIN"]
        ann_outside = ann_df[ann_df["dest_grid_id"] == "OUTSIDE_DOMAIN"]
        mean_retention = 1.0 - (ann_outside["mean_transport_fraction"].sum() / 50.0) if len(ann_outside) > 0 else 1.0
        tot_eligible_steps = ann_df["period_eligible_met_steps"].iloc[0]

        # Mean transport distance across all inside cells
        weighted_dist = (ann_inside["mean_transport_fraction"] * ann_inside["distance_km"]).sum() / ann_inside["mean_transport_fraction"].sum()

        annual_records.append({
            "year": y,
            "period_label": f"{y}-ANNUAL",
            "eligible_synoptic_steps": int(tot_eligible_steps),
            "station_synoptic_slices": int(tot_eligible_steps * 10),
            "simulation_runs": int(tot_eligible_steps * 10 * 5),
            "active_matrix_pairs": len(ann_df),
            "mean_boundary_retention_pct": round(mean_retention * 100.0, 2),
            "max_closure_error": max_err,
            "mean_transport_distance_km": round(float(weighted_dist), 2),
            "matrix_file_path": ann_out_path
        })
        print(f"  ✓ Annual {y}: {len(ann_df)} pairs | Dist: {weighted_dist:.1f} km | Closure Err: {max_err:.2e}")

    df_ann_summary = pd.DataFrame(annual_records)
    df_ann_summary.to_csv(annual_summary_csv, index=False)
    print(f"[Task B] Saved annual summary: {annual_summary_csv}")

    print("\n[Task B] 2. Generating Seasonal Transport Summaries (24 Year-Seasons + 4 Climatological)...")
    seasonal_records = []
    seasonal_dfs = {}

    # A. Yearly seasonal subsets
    for y in range(2019, 2025):
        for s_name, s_months in SEASONS_DEF.items():
            if s_name == "Winter":
                # For calendar year analysis: January, February, December of year y
                m_tuples = [(y, m) for m in [1, 2, 12]]
            else:
                m_tuples = [(y, m) for m in s_months]

            s_label = f"{y}-{s_name}"
            s_df, max_err = aggregate_monthly_subset(m_tuples, s_label)
            s_path = os.path.join(matrices_dir, f"transport_matrix_seasonal_{y}_{s_name}.csv")
            s_df.to_csv(s_path, index=False)
            seasonal_dfs[s_label] = s_df

            s_inside = s_df[s_df["dest_grid_id"] != "OUTSIDE_DOMAIN"]
            s_outside = s_df[s_df["dest_grid_id"] == "OUTSIDE_DOMAIN"]
            mean_ret = 1.0 - (s_outside["mean_transport_fraction"].sum() / 50.0) if len(s_outside) > 0 else 1.0
            tot_steps = s_df["period_eligible_met_steps"].iloc[0]
            w_dist = (s_inside["mean_transport_fraction"] * s_inside["distance_km"]).sum() / s_inside["mean_transport_fraction"].sum()

            seasonal_records.append({
                "year": y,
                "season_name": s_name,
                "period_label": s_label,
                "months_included": str(s_months),
                "season_type": "CALENDAR_YEAR_SEASON",
                "eligible_synoptic_steps": int(tot_steps),
                "active_matrix_pairs": len(s_df),
                "mean_boundary_retention_pct": round(mean_ret * 100.0, 2),
                "max_closure_error": max_err,
                "mean_transport_distance_km": round(float(w_dist), 2),
                "matrix_file_path": s_path
            })

    # B. Continuous Cross-Year Winters (DJF): Winter 2019-20, 2020-21, 2021-22, 2022-23, 2023-24
    for y_prev in range(2019, 2024):
        y_next = y_prev + 1
        m_tuples = [(y_prev, 12), (y_next, 1), (y_next, 2)]
        w_label = f"Winter_{y_prev}_{y_next}"
        w_df, max_err = aggregate_monthly_subset(m_tuples, w_label)
        w_path = os.path.join(matrices_dir, f"transport_matrix_{w_label}.csv")
        w_df.to_csv(w_path, index=False)

        w_inside = w_df[w_df["dest_grid_id"] != "OUTSIDE_DOMAIN"]
        w_outside = w_df[w_df["dest_grid_id"] == "OUTSIDE_DOMAIN"]
        mean_ret = 1.0 - (w_outside["mean_transport_fraction"].sum() / 50.0) if len(w_outside) > 0 else 1.0
        tot_steps = w_df["period_eligible_met_steps"].iloc[0]
        w_dist = (w_inside["mean_transport_fraction"] * w_inside["distance_km"]).sum() / w_inside["mean_transport_fraction"].sum()

        seasonal_records.append({
            "year": y_next,
            "season_name": "Winter_Continuous",
            "period_label": w_label,
            "months_included": f"Dec-{y_prev}, Jan-{y_next}, Feb-{y_next}",
            "season_type": "CROSS_YEAR_CONTINUOUS_WINTER",
            "eligible_synoptic_steps": int(tot_steps),
            "active_matrix_pairs": len(w_df),
            "mean_boundary_retention_pct": round(mean_ret * 100.0, 2),
            "max_closure_error": max_err,
            "mean_transport_distance_km": round(float(w_dist), 2),
            "matrix_file_path": w_path
        })

    # C. Climatological 6-Year Seasonal Baselines (Pooling all months across all 6 years)
    print("\n[Task B] 3. Generating 6-Year Climatological Seasonal Baselines...")
    climatological_dfs = {}
    for s_name, s_months in SEASONS_DEF.items():
        clim_tuples = []
        for y in range(2019, 2025):
            for m in s_months:
                clim_tuples.append((y, m))

        clim_label = f"CLIMATOLOGY_{s_name}_2019_2024"
        clim_df, max_err = aggregate_monthly_subset(clim_tuples, clim_label)
        clim_path = os.path.join(matrices_dir, f"transport_matrix_climatology_{s_name}.csv")
        clim_df.to_csv(clim_path, index=False)
        climatological_dfs[s_name] = clim_df

        c_inside = clim_df[clim_df["dest_grid_id"] != "OUTSIDE_DOMAIN"]
        c_outside = clim_df[clim_df["dest_grid_id"] == "OUTSIDE_DOMAIN"]
        mean_ret = 1.0 - (c_outside["mean_transport_fraction"].sum() / 50.0) if len(c_outside) > 0 else 1.0
        tot_steps = clim_df["period_eligible_met_steps"].iloc[0]
        w_dist = (c_inside["mean_transport_fraction"] * c_inside["distance_km"]).sum() / c_inside["mean_transport_fraction"].sum()

        seasonal_records.append({
            "year": "2019-2024",
            "season_name": s_name,
            "period_label": clim_label,
            "months_included": f"All {s_name} months (2019-2024)",
            "season_type": "SIX_YEAR_CLIMATOLOGY",
            "eligible_synoptic_steps": int(tot_steps),
            "active_matrix_pairs": len(clim_df),
            "mean_boundary_retention_pct": round(mean_ret * 100.0, 2),
            "max_closure_error": max_err,
            "mean_transport_distance_km": round(float(w_dist), 2),
            "matrix_file_path": clim_path
        })
        print(f"  ✓ 6-Year {s_name} Climatology: {len(clim_df)} pairs | Mean Dist: {w_dist:.1f} km | Closure Err: {max_err:.2e}")

    # D. Full 6-Year Baseline Matrix (all 72 months pooled)
    print("\n[Task B] 4. Generating Full 6-Year Master Climatological Baseline Matrix...")
    all_72_tuples = [(y, m) for y in range(2019, 2025) for m in range(1, 13)]
    full_6y_df, max_err = aggregate_monthly_subset(all_72_tuples, "CLIMATOLOGY_FULL_PERIOD_2019_2024")
    full_6y_path = os.path.join(matrices_dir, "transport_matrix_climatology_six_year_baseline.csv")
    full_6y_df.to_csv(full_6y_path, index=False)
    print(f"  ✓ Full 6-Year Baseline Matrix: {len(full_6y_df)} pairs | Closure Err: {max_err:.2e}")

    df_seasonal_summary = pd.DataFrame(seasonal_records)
    df_seasonal_summary.to_csv(seasonal_summary_csv, index=False)
    print(f"[Task B] Saved seasonal summary: {seasonal_summary_csv}")

    return df_ann_summary, df_seasonal_summary

if __name__ == "__main__":
    run_seasonal_and_annual_aggregation()
