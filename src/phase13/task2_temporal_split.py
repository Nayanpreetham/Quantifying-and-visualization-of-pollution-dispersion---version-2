"""
PHASE 13 — TASK 2: CHRONOLOGICAL EVALUATION PERIODS & TEMPORAL SPLIT
====================================================================
Establishes a documented chronological split across the historical years:
- Period 1: Development & Baseline Characterization (2020–2022, 36 Months)
- Period 2: Independent Validation (2023, 12 Months)
- Period 3: Final Held-Out Evaluation (2024, 12 Months)

Outputs:
- results/phase13_six_year/temporal_split_manifest.csv
- results/phase13_six_year/temporal_split_report.md
"""

import os
import sys
import pandas as pd

def create_temporal_split():
    out_dir = "results/phase13_six_year"
    os.makedirs(out_dir, exist_ok=True)

    manifest_csv = os.path.join(out_dir, "temporal_split_manifest.csv")
    report_md = os.path.join(out_dir, "temporal_split_report.md")

    # Generate monthly manifest from 2020-01 to 2024-12 (60 calendar months)
    months = pd.date_range("2020-01-01", "2024-12-31", freq="MS")
    records = []

    for m in months:
        y = m.year
        m_num = m.month
        m_str = m.strftime("%Y-%m")
        # Days in month
        days_in_m = pd.Period(m_str).days_in_month
        synoptic_steps = days_in_m * 4 # 6-hourly

        if y in [2020, 2021, 2022]:
            split_role = "DEVELOPMENT_AND_BASELINE"
            has_obs = True if y in [2020, 2021, 2022] else False
            notes = "Baseline physical dispersion characterization, seasonal climatology, and sensitivity testing"
        elif y == 2023:
            split_role = "INDEPENDENT_VALIDATION"
            has_obs = False
            notes = "Independent physical evaluation of transport matrices and boundary statistics without recalibration"
        else: # 2024
            split_role = "FINAL_HELD_OUT_TEST"
            has_obs = False
            notes = "Untouched held-out benchmark for multi-year transport stability"

        records.append({
            "month_str": m_str,
            "year": y,
            "month": m_num,
            "days_in_month": days_in_m,
            "synoptic_steps": synoptic_steps,
            "split_role": split_role,
            "era5_wind_ready": True,
            "ground_openaq_available": has_obs,
            "scientific_purpose": notes
        })

    df_manifest = pd.DataFrame(records)
    df_manifest.to_csv(manifest_csv, index=False)
    print(f"[Task 2 Split] Saved temporal split manifest: {manifest_csv} ({len(df_manifest)} months)")

    # Grouped summary
    split_summary = df_manifest.groupby("split_role").agg(
        total_months=("month_str", "count"),
        total_synoptic_steps=("synoptic_steps", "sum"),
        min_month=("month_str", "min"),
        max_month=("month_str", "max")
    ).reset_index()

    # Markdown Report
    lines = [
        "# Phase 13 — Task 2: Chronological Evaluation Periods & Temporal Split",
        "",
        "## 1. Executive Summary & Split Rationale",
        "",
        "A rigorous chronological evaluation framework was established for the 5-year continuous historical record (2020–2024, 60 calendar months, 7,308 synoptic steps).",
        "",
        "> [!IMPORTANT]",
        "> **Scientific Framing of Physical Evaluation Periods**:",
        "> The 2D Lagrangian dispersion model is a **physics-based kinematic engine with zero ML training parameters**. Therefore, these temporal splits are established for:",
        "> 1. **Baseline Characterization & Calibration (2020–2022)**: Parameter sensitivity checks, boundary loss verification, and baseline transport climatology.",
        "> 2. **Independent Validation (2023)**: Evaluation of inter-annual transport variability and boundary stability on unseen meteorological forcing.",
        "> 3. **Final Held-Out Evaluation (2024)**: Completely untouched evaluation period to prevent methodology overfitting or retrospective tuning.",
        "> 4. **Future Surrogate Boundary Protection**: If a machine-learning surrogate model is subsequently approved, this manifest provides the strict temporal boundaries required to prevent cross-year data leakage.",
        "",
        "## 2. Chronological Split Summary Table",
        "",
        "| Split Category | Years Included | Months | Synoptic Steps | Ground PM2.5 Data | Scientific Role |",
        "|---|:---:|:---:|:---:|:---:|---|"
    ]

    for _, r in split_summary.iterrows():
        role = r["split_role"]
        obs_status = "Available (35,141 obs)" if "DEVELOPMENT" in role else "Meteorology-only"
        lines.append(
            f"| **{role}** | {r['min_month'][:4]}–{r['max_month'][:4]} | "
            f"{r['total_months']} | {r['total_synoptic_steps']:,} | {obs_status} | "
            f"{'Baseline parameterization & dispersion physics' if 'DEVELOPMENT' in role else ('Independent validation' if 'VALIDATION' in role else 'Held-out final benchmark')} |"
        )

    lines.extend([
        "",
        "## 3. Preservation of Final Held-Out Test Integrity",
        "",
        "- **No Parameter Tuning**: The 2024 final-test period will never be used to tune turbulent diffusion coefficients ($\sigma$), advection window definitions, or boundary thresholds.",
        "- **Contiguous Temporal Blocks**: Years are partitioned in strict chronological order (2020–2022 $\\to$ 2023 $\\to$ 2024). No random shuffling or k-fold interleaving of individual hours is permitted.",
        "- **6-Year Extension Path**: When 2019 ERA5 wind data is acquired, it will be assigned to the Baseline Development period (creating a 2019–2022 4-year development block, exactly matching the 4-1-1 architecture)."
    ])

    with open(report_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Task 2 Split] Saved temporal split Markdown report: {report_md}")

    return df_manifest

if __name__ == "__main__":
    create_temporal_split()
