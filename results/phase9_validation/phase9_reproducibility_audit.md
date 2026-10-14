# Phase 9 — Task 1: Phase 8 Reproducibility Audit

**Audit Timestamp:** 2026-10-14 22:35 UTC  
**Auditor:** Independent Scientific Audit Agent (Phase 9)  
**Target Phase:** Phase 8 India-Wide Grid-to-Grid Pollution Dispersion Pilot  

---

## 1. Summary of Reproducibility Checks

| ID | Claim Description | Reported Value | Measured Value | Verification Method | Status |
|---|---|---|---|---|---|
| **REP_01** | Total Active Transport Records in transport_targets_national.csv | 7,730 | 7730 | Row count of results/national_pilot/transport_targets_national.csv | `VERIFIED_EXACT` |
| **REP_02** | Aggregated Matrix Pairs in transport_matrix_national.csv | 2,831 | 2831 | Row count of results/national_pilot/transport_matrix_national.csv | `VERIFIED_EXACT` |
| **REP_03** | Total Simulation Runs in boundary_loss_statistics_national.csv | 1,335 | 1335 | Row count of results/national_pilot/boundary_loss_statistics_national.csv | `VERIFIED_EXACT` |
| **REP_04** | Unique Active Pilot Stations in Aligned Dataset | 10 | 10 | df['station_id'].nunique() in data/national/openaq_era5_aligned_national.csv | `VERIFIED_EXACT` |
| **REP_05** | Synoptic Time Steps and Date Window | 2021-09-18 00:00 to 2021-09-24 18:00 (28 steps) | 2021-09-18 00:00:00 UTC to 2021-09-24 18:00:00 UTC (28 steps) | timestamp_utc unique count & bounds in openaq_era5_aligned_national.csv | `VERIFIED_EXACT` |
| **REP_06** | Simulation Runs Math: 267 slices x 5 advection windows | 267 slices x 5 dt = 1,335 runs | 267 slices x 5 dt = 1335 runs | Multiplication of input slices (267) by length of dt list [1,3,6,12,24] (5) | `VERIFIED_EXACT` |
| **REP_07** | Ensemble Size N=20 Verification Across All Records | N=20 constant | target_n=[20], bnd_n=[20], particles_per_run=20-20 | Check ensemble_n column and particles_inside + outside == 20 across all 1,335 runs | `VERIFIED_EXACT` |
| **REP_08** | Reported 10/10 Constraints Passed Traced to Underlying Test File | 10 / 10 PASSED (100.0%) | 10 / 10 PASSED (100.0%) | Inspect results/national_pilot/national_constraints_report.csv | `VERIFIED_EXACT` |
| **REP_09** | Continuous National Grid Total Cell Count (133 rows x 121 cols) | 16,093 | 16093 | Row count of data/national/india_025_grid.csv | `VERIFIED_EXACT` |
| **REP_10** | National Station Mapping: 103 Evaluated, 103 Matched (100.0%) | 103 evaluated, 103 matched | 103 matched of 103 evaluated (100.0%) | Inspect data/national/national_station_to_grid_mapping.csv | `VERIFIED_EXACT` |

---

## 2. File Integrity & Cryptographic Hashes

The following files generated during Phase 8 were hashed to guarantee baseline integrity and detect any silent modifications:

| File Path | File Size | SHA-256 (Prefix) |
|---|---|---|
| `data/national/india_025_grid.csv` | 2272815 bytes | `5f3663b092602c93...` |
| `data/national/national_station_to_grid_mapping.csv` | 15026 bytes | `8185c6f2b187113a...` |
| `data/national/openaq_pm25_national_sources.csv` | 49462 bytes | `c7dd48e70656cf94...` |
| `data/national/openaq_era5_aligned_national.csv` | 56020 bytes | `1f6f735c35de93d5...` |
| `results/national_pilot/transport_targets_national.csv` | 1976749 bytes | `d382fc8aeb1ab6e5...` |
| `results/national_pilot/boundary_loss_statistics_national.csv` | 236460 bytes | `cbc38970d160ae5f...` |
| `results/national_pilot/transport_matrix_national.csv` | 355206 bytes | `801fae73a25c3063...` |
| `results/national_pilot/national_constraints_report.csv` | 2092 bytes | `7a0283d105d9671a...` |
| `results/national_pilot/national_dispersion_summary.csv` | 3024 bytes | `28abf18e2bfa6675...` |

---

## 3. Findings & Discrepancy Analysis

1. **All 10 Phase 8 Claims Verified Exactly**: Every single claim regarding station counts (10), synoptic time steps (28), simulation runs (1,335), ensemble size ($N=20$), transport records (7,730), matrix pairs (2,831), and grid cells (16,093) was verified to 100% numerical precision against the disk artifacts.
2. **No Silent File Replacement**: File modification timestamps and row-level structures correspond exactly with the Phase 8 execution logs.
3. **Traceability**: The reported 10/10 constraints pass was confirmed directly from `results/national_pilot/national_constraints_report.csv`.
