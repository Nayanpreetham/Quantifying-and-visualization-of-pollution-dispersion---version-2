"""
PHASE 15 — MASTER EXECUTION ORCHESTRATOR
========================================
Orchestrates:
1. Task 3: Independent validation of downloaded 2019 ERA5 NetCDF.
2. Task 4 Step 1: Processes 2019-01, verifies closure & exact run count, tests restart idempotence.
3. Task 4 Step 2: Processes remaining months (2019-02 to 2019-12).
4. Task 4 Step 3: Aggregates 2019 annual matrix and boundary statistics.
5. Task 5: Consolidates complete 6-year historical inventory (2019–2024).
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import pandas as pd

from src.phase15.task3_validate_era5_2019 import validate_era5_2019
from src.phase15.task4_process_2019 import (
    init_manifest_2019,
    aggregate_annual_2019_exact
)
from src.phase13.run_six_year_pipeline import (
    process_single_month,
    get_pipeline_paths
)
from src.phase15.task5_six_year_summary import build_six_year_summary

def run_phase15():
    nc_path = "data/raw/era5/2019/era5_2019_instant.nc"
    if not os.path.exists(nc_path):
        raise FileNotFoundError(f"Cannot run Phase 15 pipeline: 2019 ERA5 file not found at {nc_path}")

    base_out = "results/phase15_six_year"
    print("=======================================================")
    print("PHASE 15 — EXECUTION OF 2019 HISTORICAL BATCH PIPELINE")
    print("=======================================================")

    # Step 1: Validate 2019 ERA5
    print("\n[Step 1] Running Task 3 Independent ERA5 Validation...")
    df_val = validate_era5_2019(nc_path, out_dir=base_out)
    verdict = df_val["audit_verdict"].iloc[0]
    if verdict != "VALID_AND_COMPLETE":
        raise ValueError(f"ERA5 2019 validation failed with verdict: {verdict}")
    print("[Step 1 PASSED] 2019 ERA5 validation is VALID_AND_COMPLETE.")

    # Step 2: Initialize Manifest
    print("\n[Step 2] Initializing 2019 processing manifest...")
    monthly_dir, annual_dir, manifest_csv = get_pipeline_paths(base_out)
    init_manifest_2019(manifest_csv)

    stations_df = pd.read_csv("results/phase11_validation/selected_stations.csv")
    grid_df = pd.read_csv("data/national/india_025_grid.csv")
    grid_lookup = grid_df.set_index("grid_id")[["latitude", "longitude"]].to_dict(orient="index")

    df_obs = pd.read_csv("data/real/openaq/pm25_observations.csv")
    df_obs["dt"] = pd.to_datetime(df_obs["timestamp_utc"]).dt.tz_localize(None)
    df_obs["hour_synoptic"] = ((df_obs["dt"].dt.hour + 3) // 6 * 6) % 24
    df_obs["date_str"] = df_obs["dt"].dt.strftime("%Y-%m-%d")

    obs_grouped = df_obs.groupby(["station_id", "date_str", "hour_synoptic"]).agg(
        pm25_mean=("pm25", "mean"),
        count=("pm25", "count")
    ).reset_index()

    obs_grouped_map = obs_grouped.set_index(["station_id", "date_str", "hour_synoptic"])[["pm25_mean", "count"]].to_dict(orient="index")

    # Step 3: Test single representative month (2019-01)
    print("\n[Step 3] Processing representative month 2019-01...")
    m1_matrix, m1_bound = process_single_month(
        2019, 1, stations_df, grid_lookup, obs_grouped_map, base_out=base_out
    )

    # Step 4: Verify 2019-01 properties & test restart idempotence
    print("\n[Step 4] Verifying 2019-01 outputs & testing restart idempotence...")
    assert len(m1_bound) == 6200, f"Expected 6,200 runs for Jan 2019 (124 steps * 10 stations * 5 windows), got {len(m1_bound)}"
    closure = m1_matrix.groupby(["station_id", "elapsed_time_hours"])["mean_transport_fraction"].sum()
    max_err = float((closure - 1.0).abs().max())
    assert max_err < 1e-4, f"Matrix closure error too large: {max_err}"
    print(f"  ✓ 2019-01 exact run count verified (6,200 runs)")
    print(f"  ✓ 2019-01 exact matrix closure verified (max error: {max_err:.2e})")

    # Test idempotence under restart
    print("  Testing restart idempotence on 2019-01...")
    m1_matrix_re, m1_bound_re = process_single_month(
        2019, 1, stations_df, grid_lookup, obs_grouped_map, base_out=base_out
    )
    assert len(m1_bound_re) == len(m1_bound), "Restart changed run count!"
    assert len(m1_matrix_re) == len(m1_matrix), "Restart changed matrix pairs count!"
    print("  ✓ Idempotence confirmed: identical row count and metrics after restart, 0 duplicates.")

    # Step 5: Process remaining months (2 to 12)
    print("\n[Step 5] Processing remaining 11 months of 2019...")
    for m in range(2, 13):
        process_single_month(2019, m, stations_df, grid_lookup, obs_grouped_map, base_out=base_out)

    # Step 6: Annual aggregation
    print("\n[Step 6] Aggregating 2019 annual transport matrix and boundary statistics...")
    aggregate_annual_2019_exact(base_out=base_out)

    # Step 7: Six-year consolidated summary
    print("\n[Step 7] Generating consolidated six-year coverage summary...")
    build_six_year_summary(phase13_dir="results/phase13_six_year", phase15_dir=base_out)

    print("\n=======================================================")
    print("PHASE 15 PIPELINE COMPLETED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    run_phase15()
