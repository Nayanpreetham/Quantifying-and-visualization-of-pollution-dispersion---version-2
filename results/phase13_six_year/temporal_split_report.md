# Phase 13 — Task 2: Chronological Evaluation Periods & Temporal Split

## 1. Executive Summary & Split Rationale

A rigorous chronological evaluation framework was established for the 5-year continuous historical record (2020–2024, 60 calendar months, 7,308 synoptic steps).

> [!IMPORTANT]
> **Scientific Framing of Physical Evaluation Periods**:
> The 2D Lagrangian dispersion model is a **physics-based kinematic engine with zero ML training parameters**. Therefore, these temporal splits are established for:
> 1. **Baseline Characterization & Calibration (2020–2022)**: Parameter sensitivity checks, boundary loss verification, and baseline transport climatology.
> 2. **Independent Validation (2023)**: Evaluation of inter-annual transport variability and boundary stability on unseen meteorological forcing.
> 3. **Final Held-Out Evaluation (2024)**: Completely untouched evaluation period to prevent methodology overfitting or retrospective tuning.
> 4. **Future Surrogate Boundary Protection**: If a machine-learning surrogate model is subsequently approved, this manifest provides the strict temporal boundaries required to prevent cross-year data leakage.

## 2. Chronological Split Summary Table

| Split Category | Years Included | Months | Synoptic Steps | Ground PM2.5 Data | Scientific Role |
|---|:---:|:---:|:---:|:---:|---|
| **DEVELOPMENT_AND_BASELINE** | 2020–2022 | 36 | 4,384 | Available (35,141 obs) | Baseline parameterization & dispersion physics |
| **FINAL_HELD_OUT_TEST** | 2024–2024 | 12 | 1,464 | Meteorology-only | Held-out final benchmark |
| **INDEPENDENT_VALIDATION** | 2023–2023 | 12 | 1,460 | Meteorology-only | Independent validation |

## 3. Preservation of Final Held-Out Test Integrity

- **No Parameter Tuning**: The 2024 final-test period will never be used to tune turbulent diffusion coefficients ($\sigma$), advection window definitions, or boundary thresholds.
- **Contiguous Temporal Blocks**: Years are partitioned in strict chronological order (2020–2022 $\to$ 2023 $\to$ 2024). No random shuffling or k-fold interleaving of individual hours is permitted.
- **6-Year Extension Path**: When 2019 ERA5 wind data is acquired, it will be assigned to the Baseline Development period (creating a 2019–2022 4-year development block, exactly matching the 4-1-1 architecture).