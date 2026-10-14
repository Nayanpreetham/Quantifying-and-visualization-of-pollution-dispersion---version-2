"""
PHASE 10: NATIONAL TRANSPORT MATRIX TIME AGGREGATION ENGINE
============================================================
Corrects the time-aggregation defect in the national transport matrix:
1. Reads per-step transport records from results/national_pilot/transport_targets_national.csv.
2. Identifies eligible simulation steps for each source station and advection window from
   results/national_pilot/boundary_loss_statistics_national.csv.
3. Computes the true unconditional time-mean transport probability:
   T_bar[src, dest, dt] = sum(T[src, dest, t, dt]) / N_eligible(src, dt)
   where T = 0 for valid time steps where the destination received zero particles.
4. Corrects outside-domain transport symmetrically using the same eligible denominator:
   T_bar[src, OUTSIDE, dt] = sum(T_outside[src, t, dt]) / N_eligible(src, dt)
5. Produces side-by-side comparison between old (conditional) and corrected (unconditional) matrices.
6. Conducts closure verification for every source and time window:
   sum(T_bar_inside) + T_bar_outside == 1.0000 strictly.

Outputs:
- results/phase10_matrix_fix/transport_matrix_national_corrected.csv
- results/phase10_matrix_fix/transport_matrix_closure_audit.csv
- results/phase10_matrix_fix/aggregation_comparison.csv
"""

import os
import sys
import pandas as pd
import numpy as np

DATA_LABEL = "NATIONAL DATA — CONTINUOUS INDIA 0.25° GRID (PHASE 10 CORRECTED AGGREGATION)"

def correct_transport_matrix(targets_path="results/national_pilot/transport_targets_national.csv",
                             bnd_path="results/national_pilot/boundary_loss_statistics_national.csv",
                             old_matrix_path="results/national_pilot/transport_matrix_national.csv",
                             out_dir="results/phase10_matrix_fix"):
    os.makedirs(out_dir, exist_ok=True)
    corrected_matrix_path = os.path.join(out_dir, "transport_matrix_national_corrected.csv")
    closure_audit_path = os.path.join(out_dir, "transport_matrix_closure_audit.csv")
    comparison_path = os.path.join(out_dir, "aggregation_comparison.csv")

    print(f"[Phase 10 Engine] Loading per-step targets: {targets_path}")
    targets_df = pd.read_csv(targets_path)
    bnd_df = pd.read_csv(bnd_path)
    old_matrix_df = pd.read_csv(old_matrix_path)

    # -------------------------------------------------------------
    # Step 1: Determine Eligible Simulation Steps per (station_id, dt)
    # -------------------------------------------------------------
    # In bnd_df, every valid simulation run has one row
    eligible_steps_df = bnd_df.groupby(["station_id", "elapsed_time_hours"]).agg(
        eligible_steps_count=("timestamp_utc", "count")
    ).reset_index()

    # -------------------------------------------------------------
    # Step 2: Sum Transport Fractions & Influences for Inside Destination Cells
    # -------------------------------------------------------------
    inside_grouped = targets_df.groupby([
        "station_id", "station_name", "city", "source_grid_id", "dest_grid_id", "elapsed_time_hours"
    ]).agg(
        sum_transport_fraction=("transport_fraction", "sum"),
        max_transport_fraction=("transport_fraction", "max"),
        sum_transport_influence=("transport_influence", "sum"),
        max_transport_influence=("transport_influence", "max"),
        visited_steps_count=("transport_fraction", "count"),
        distance_km=("distance_km", "first"),
        rel_angle_deg=("rel_angle_to_wind_deg", "mean")
    ).reset_index()

    # Merge with eligible steps count to compute TRUE unconditional time-mean
    inside_corrected = pd.merge(inside_grouped, eligible_steps_df, on=["station_id", "elapsed_time_hours"], how="inner")
    inside_corrected["mean_transport_fraction"] = inside_corrected["sum_transport_fraction"] / inside_corrected["eligible_steps_count"]
    inside_corrected["mean_transport_influence"] = inside_corrected["sum_transport_influence"] / inside_corrected["eligible_steps_count"]
    inside_corrected["data_label"] = DATA_LABEL

    # -------------------------------------------------------------
    # Step 3: Outside Domain Sinks using Symmetrical Eligible Denominator
    # -------------------------------------------------------------
    outside_grouped = bnd_df.groupby([
        "station_id", "station_name", "city", "source_grid_id", "elapsed_time_hours"
    ]).agg(
        sum_outside_fraction=("boundary_loss_fraction", "sum"),
        max_outside_fraction=("boundary_loss_fraction", "max"),
        sum_outside_influence=("outside_influence", "sum"),
        max_outside_influence=("outside_influence", "max"),
        eligible_steps_count=("boundary_loss_fraction", "count"),
        visited_steps_count=("particles_outside", lambda s: int((s > 0).sum()))
    ).reset_index()

    # Filter to cases where outside fraction is non-zero
    outside_active = outside_grouped[outside_grouped["max_outside_fraction"] > 0.0].copy()
    outside_rows = []
    for _, r in outside_active.iterrows():
        n_elig = r["eligible_steps_count"]
        mean_out_frac = r["sum_outside_fraction"] / n_elig
        mean_out_inf = r["sum_outside_influence"] / n_elig
        outside_rows.append({
            "station_id": int(r["station_id"]),
            "station_name": r["station_name"],
            "city": r["city"],
            "source_grid_id": r["source_grid_id"],
            "dest_grid_id": "OUTSIDE_DOMAIN",
            "elapsed_time_hours": float(r["elapsed_time_hours"]),
            "sum_transport_fraction": float(r["sum_outside_fraction"]),
            "max_transport_fraction": float(r["max_outside_fraction"]),
            "sum_transport_influence": float(r["sum_outside_influence"]),
            "max_transport_influence": float(r["max_outside_influence"]),
            "visited_steps_count": int(r["visited_steps_count"]),
            "distance_km": np.nan,
            "rel_angle_deg": np.nan,
            "eligible_steps_count": int(n_elig),
            "mean_transport_fraction": float(mean_out_frac),
            "mean_transport_influence": float(mean_out_inf),
            "data_label": DATA_LABEL
        })

    if outside_rows:
        df_outside_rows = pd.DataFrame(outside_rows)
        combined_matrix = pd.concat([inside_corrected, df_outside_rows], ignore_index=True)
    else:
        combined_matrix = inside_corrected

    # Clean formatting and column order
    cols_order = [
        "station_id", "station_name", "city", "source_grid_id", "dest_grid_id",
        "elapsed_time_hours", "mean_transport_fraction", "max_transport_fraction",
        "mean_transport_influence", "max_transport_influence", "distance_km",
        "rel_angle_deg", "eligible_steps_count", "visited_steps_count", "data_label"
    ]
    combined_matrix = combined_matrix[cols_order].sort_values(
        ["station_id", "elapsed_time_hours", "dest_grid_id"]
    ).reset_index(drop=True)

    combined_matrix.to_csv(corrected_matrix_path, index=False)
    print(f"[Phase 10 Engine] Saved corrected national transport matrix: {corrected_matrix_path} ({len(combined_matrix)} pairs)")

    # -------------------------------------------------------------
    # Step 4: Strict Matrix Closure Audit
    # -------------------------------------------------------------
    inside_sums = combined_matrix[combined_matrix["dest_grid_id"] != "OUTSIDE_DOMAIN"].groupby(
        ["station_id", "station_name", "city", "elapsed_time_hours"]
    )["mean_transport_fraction"].sum().reset_index(name="sum_inside_fractions")

    outside_sums = combined_matrix[combined_matrix["dest_grid_id"] == "OUTSIDE_DOMAIN"].groupby(
        ["station_id", "elapsed_time_hours"]
    )["mean_transport_fraction"].sum().reset_index(name="outside_fraction")

    closure_df = pd.merge(inside_sums, outside_sums, on=["station_id", "elapsed_time_hours"], how="left")
    closure_df["outside_fraction"] = closure_df["outside_fraction"].fillna(0.0)
    closure_df["total_closure_sum"] = closure_df["sum_inside_fractions"] + closure_df["outside_fraction"]
    closure_df["closure_error"] = np.abs(closure_df["total_closure_sum"] - 1.0)
    closure_df["closure_status"] = np.where(closure_df["closure_error"] < 1e-5, "STRICTLY_CLOSED_1.0000", "CLOSURE_VIOLATION")

    closure_df.to_csv(closure_audit_path, index=False)
    max_err = closure_df["closure_error"].max()
    print(f"[Phase 10 Engine] Saved closure audit: {closure_audit_path} (Max error: {max_err:.2e})")

    # -------------------------------------------------------------
    # Step 5: Side-by-Side Aggregation Comparison (Old vs Corrected)
    # -------------------------------------------------------------
    old_sub = old_matrix_df[[
        "station_id", "dest_grid_id", "elapsed_time_hours",
        "mean_transport_fraction", "mean_transport_influence"
    ]].rename(columns={
        "mean_transport_fraction": "old_mean_transport_fraction",
        "mean_transport_influence": "old_mean_transport_influence"
    })

    comp_df = pd.merge(
        combined_matrix,
        old_sub,
        on=["station_id", "dest_grid_id", "elapsed_time_hours"],
        how="inner"
    )
    comp_df["inflation_ratio"] = comp_df["old_mean_transport_fraction"] / comp_df["mean_transport_fraction"].replace(0, np.nan)
    comp_df["theoretical_inflation_ratio"] = comp_df["eligible_steps_count"] / comp_df["visited_steps_count"]
    comp_df["ratio_discrepancy"] = np.abs(comp_df["inflation_ratio"] - comp_df["theoretical_inflation_ratio"])

    # Select representative cases: frequent vs infrequent visits
    comp_summary_cols = [
        "station_id", "station_name", "city", "dest_grid_id", "elapsed_time_hours",
        "eligible_steps_count", "visited_steps_count",
        "old_mean_transport_fraction", "mean_transport_fraction",
        "old_mean_transport_influence", "mean_transport_influence",
        "inflation_ratio"
    ]
    comp_df[comp_summary_cols].to_csv(comparison_path, index=False)
    print(f"[Phase 10 Engine] Saved aggregation comparison: {comparison_path} ({len(comp_df)} pairs compared)")

    return combined_matrix, closure_df, comp_df

if __name__ == "__main__":
    correct_transport_matrix()
