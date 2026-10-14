# Phase 13 — Historical National Pollution Dispersion Processing Report

- **Historical Window**: 2020–2024 (5 Complete Calendar Years, 60 Months)
- **Total Completed Months**: 60 / 60
- **Total Synoptic Steps**: 73,080 steps
- **Total Simulation Runs**: 365,400 runs
- **Final Milestone Status**: **COMPLETE WITH GAPS**

## 1. Executive Summary

Phase 13 transitioned the 2D grid-to-grid pollution dispersion model from short validation pilots to full historical production across India:
1. **Continuous 5-Year Historical Processing**: Successfully processed **60 calendar months** spanning **January 1, 2020 through December 31, 2024** without interruption.
2. **Zero-Leakage Temporal Splitting**:
   - **2020–2022 (36 Months)**: Development & Baseline Characterization (incorporating 35,141 coupled OpenAQ PM2.5 observations).
   - **2023 (12 Months)**: Independent Validation Period.
   - **2024 (12 Months)**: Untouched Final Held-Out Evaluation Period.
3. **Rigorous Numerical Integrity**: Every monthly and annual matrix satisfies exact probability closure ($\sum \bar{T} = 1.000000 \pm 10^{-5}$ across all source-window groups).
4. **Status Regarding 6th Year (2019)**: OpenAQ observations exist for 2019, but ERA5 surface wind NetCDF files are missing on disk. In accordance with non-negotiable preservation rules, this missing year is documented as an external data requirement rather than synthesized.

## 2. Annual Historical Processing Summary Table

| Year | Months | Synoptic Steps | Total Runs | Observed PM2.5 Steps | Unmonitored Steps | Matrix Pairs | Boundary Retention | Max Closure Error | Runtime (s) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2020** | 12 | 14,640 | 73,200 | 14 | 14,626 | 15,394 | 99.99% | `1.87e-14` | 78.5s |
| **2021** | 12 | 14,600 | 73,000 | 2,377 | 12,223 | 17,171 | 99.98% | `1.98e-14` | 69.5s |
| **2022** | 12 | 14,600 | 73,000 | 0 | 14,600 | 15,892 | 100.0% | `1.97e-14` | 69.5s |
| **2023** | 12 | 14,600 | 73,000 | 0 | 14,600 | 15,629 | 100.0% | `1.89e-14` | 69.8s |
| **2024** | 12 | 14,640 | 73,200 | 0 | 14,640 | 17,426 | 100.0% | `1.97e-14` | 66.3s |

## 3. Computational Performance & Storage Efficiency

- **Total Processing Runtime**: `353.6` seconds (~`5.89` minutes) for 365,400 simulation runs.
- **Average Throughput**: `1033.4` runs / second.
- **Peak RAM Footprint**: `< 200 MB` throughout the entire 5-year run due to monthly NetCDF resource chunking.
- **Storage Footprint**: Sparse CSV storage compressed 5 years of hourly national dispersion into under `35 MB` across all monthly and annual outputs.

## 4. Preservation & Scientific Non-Regression Confirmation

- **Phases 1–12 Outputs**: Confirmed 100% untouched and preserved.
- **Physical Methodology**: Retained standard 2D kinematic advection and Gaussian ensemble ($N=20$).
- **Zero Imputation**: Missing ground observations were left un-imputed; pure meteorological transport was computed unconditionally across all 7,308 valid wind steps.

## 5. Final Milestone Status: COMPLETE WITH GAPS

The historical national pipeline is operational, restartable, and complete for all 5 verified historical years (2020–2024). Processing for 2019 will unlock automatically once `era5_2019_instant.nc` is placed in `data/raw/era5/`.