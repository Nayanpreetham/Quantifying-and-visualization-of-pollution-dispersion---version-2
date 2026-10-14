"""
PHASE 15 — TASK 6: SIX-YEAR CHRONOLOGICAL EVALUATION SPLITS MANIFEST
====================================================================
Generates results/phase15_six_year/six_year_evaluation_splits.csv
defining the strict chronological boundaries across all 72 months (2019–2024):
- 2019–2022 (48 months): DEVELOPMENT_AND_BASELINE (includes 2020/2021 empirical PM2.5 conditioning)
- 2023 (12 months): VALIDATION (meteorological transport climatology)
- 2024 (12 months): HELD_OUT_TEST (strictly held out, zero parameter tuning)
"""

import os
import calendar
import pandas as pd

def generate_evaluation_splits(out_dir="results/phase15_six_year"):
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "six_year_evaluation_splits.csv")

    rows = []
    for y in range(2019, 2025):
        if y <= 2022:
            role = "DEVELOPMENT_AND_BASELINE"
        elif y == 2023:
            role = "VALIDATION"
        else:
            role = "HELD_OUT_TEST"

        for m in range(1, 13):
            days = calendar.monthrange(y, m)[1]
            steps = days * 4
            rows.append({
                "month_str": f"{y:04d}-{m:02d}",
                "calendar_year": y,
                "month_num": m,
                "days_in_month": days,
                "synoptic_6h_steps": steps,
                "station_synoptic_slices": steps * 10,
                "ensemble_simulation_runs": steps * 10 * 5,
                "split_role": role,
                "evaluation_scope": (
                    "Baseline physical transport & empirical PM2.5 observation conditioning"
                    if y in [2020, 2021] else
                    "Meteorological physical transport climatology (unconditioned)"
                )
            })

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    print(f"[Task 6] Saved 72-month evaluation splits manifest: {out_csv}")
    return df

if __name__ == "__main__":
    generate_evaluation_splits()
