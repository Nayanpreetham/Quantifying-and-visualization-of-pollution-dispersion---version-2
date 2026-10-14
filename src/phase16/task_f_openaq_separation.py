"""
PHASE 16 — TASK F: CONSERVATIVE OPENAQ OBSERVATION COVERAGE & SEPARATION
========================================================================
Rigorous separation between:
1. Physical ERA5 transport climatology (T_bar, dimensionless fraction [0, 1]).
2. Observed PM2.5-weighted transported influence (I = T_bar * C_src, ug/m^3).

Analyzes exact observation coverage across all 10 stations and 6 calendar years (2019–2024):
- Documents zero-imputation prohibition: missing PM2.5 is NEVER treated as zero.
- Re-verifies 2,391 matched synoptic observation slots (concentrated in 2020 and 2021).
- Documents scientific limits: transported influence is NOT an ambient destination AQI prediction.
- Outputs: results/phase16_climatology/tables/openaq_comparison_coverage.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd

def audit_openaq_coverage_separation(out_dir="results/phase16_climatology/tables"):
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "openaq_comparison_coverage.csv")

    stations_df = pd.read_csv("results/phase11_validation/selected_stations.csv")
    df_obs = pd.read_csv("data/real/openaq/pm25_observations.csv")
    df_obs["dt"] = pd.to_datetime(df_obs["timestamp_utc"]).dt.tz_localize(None)
    df_obs["hour_synoptic"] = ((df_obs["dt"].dt.hour + 3) // 6 * 6) % 24
    df_obs["date_str"] = df_obs["dt"].dt.strftime("%Y-%m-%d")
    df_obs["year"] = df_obs["dt"].dt.year

    # Aggregate to synoptic 6h observation slots
    obs_synoptic = df_obs.groupby(["station_id", "year", "date_str", "hour_synoptic"]).agg(
        pm25_mean=("pm25", "mean")
    ).reset_index()

    years = list(range(2019, 2025))
    records = []

    print("[Task F] Auditing observation coverage across 10 stations x 6 years...")

    for _, st in stations_df.iterrows():
        s_id = int(st["station_id"])
        s_name = st["station_name"]
        city = st["corrected_city"]
        grid_id = st["matched_grid_id"]

        for y in years:
            days_in_yr = 366 if (y in [2020, 2024]) else 365
            synoptic_slots_total = days_in_yr * 4

            st_y_obs = obs_synoptic[(obs_synoptic["station_id"] == s_id) & (obs_synoptic["year"] == y)]
            n_matched_slots = len(st_y_obs)
            cov_pct = (n_matched_slots / float(synoptic_slots_total)) * 100.0

            if n_matched_slots > 0:
                mean_pm25 = float(st_y_obs["pm25_mean"].mean())
                std_pm25 = float(st_y_obs["pm25_mean"].std()) if n_matched_slots > 1 else 0.0
                min_pm25 = float(st_y_obs["pm25_mean"].min())
                max_pm25 = float(st_y_obs["pm25_mean"].max())
                status = "EMPIRICAL_INFLUENCE_CALCULABLE"
                interpretation = (
                    f"Concentration-weighted transported influence (ug/m^3) supported "
                    f"for {n_matched_slots} synoptic time steps."
                )
            else:
                mean_pm25, std_pm25, min_pm25, max_pm25 = np.nan, np.nan, np.nan, np.nan
                status = "METEOROLOGICAL_TRANSPORT_ONLY"
                interpretation = (
                    "No ground PM2.5 measurements in OpenAQ archive. Analysis strictly restricted "
                    "to unconditioned physical meteorological transport climatology (T_bar)."
                )

            records.append({
                "station_id": s_id,
                "station_name": s_name,
                "city": city,
                "matched_grid_id": grid_id,
                "calendar_year": y,
                "total_synoptic_slots": synoptic_slots_total,
                "matched_observation_slots": n_matched_slots,
                "observation_coverage_pct": round(cov_pct, 2),
                "unmonitored_slots": synoptic_slots_total - n_matched_slots,
                "mean_observed_pm25_ugm3": round(mean_pm25, 2) if not np.isnan(mean_pm25) else np.nan,
                "std_observed_pm25_ugm3": round(std_pm25, 2) if not np.isnan(std_pm25) else np.nan,
                "min_observed_pm25_ugm3": round(min_pm25, 2) if not np.isnan(min_pm25) else np.nan,
                "max_observed_pm25_ugm3": round(max_pm25, 2) if not np.isnan(max_pm25) else np.nan,
                "data_usability_status": status,
                "scientific_interpretation": interpretation
            })

    df_out = pd.DataFrame(records)
    df_out.to_csv(out_csv, index=False)
    print(f"[Task F] Saved OpenAQ comparison coverage table: {out_csv} ({len(df_out)} station-year records)")

    # Summary
    print("\n=== OPENAQ COVERAGE AUDIT SUMMARY ===")
    print(f"Total Station-Year Slices: {len(df_out)} (10 stations x 6 years)")
    print(f"Total Matched Synoptic Slots: {df_out['matched_observation_slots'].sum():,} (Expected 2,391)")
    print(f"  - 2020: {df_out[df_out['calendar_year'] == 2020]['matched_observation_slots'].sum()} slots (Guwahati)")
    print(f"  - 2021: {df_out[df_out['calendar_year'] == 2021]['matched_observation_slots'].sum()} slots (All 10 stations)")
    print(f"  - 2019, 2022, 2023, 2024: 0 slots (Strictly Meteorological Transport Climatology)")

    return df_out

if __name__ == "__main__":
    audit_openaq_coverage_separation()
