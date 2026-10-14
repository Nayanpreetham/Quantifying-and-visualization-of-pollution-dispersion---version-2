# Phase 10 — National Transport Matrix Time-Aggregation Fix & Regression Report

**Project:** 2D Grid-to-Grid Pollution Dispersion Model for India  
**Scope:** Minimal Algorithmic Correction of Temporal Aggregation & Regression Verification  
**Evaluation Dates:** September 18–24, 2021 (7 Synoptic Days, 28 Six-Hourly Steps)  
**Target:** National Transport Matrix ($0.25^\circ \times 0.25^\circ$ Grid, 16,093 Cells)  
**Status:** Defect Fully Resolved, All 7 Regression Tests Passed (100.0%)  
**Final Decision:** **GO FOR SCALE-UP / PRODUCTION PREPARATION**  

---

## 1. Executive Summary & Root Cause Analysis

In Phase 9, an independent scientific audit identified that while instantaneous synoptic transport records in [`transport_targets_national.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/national_pilot/transport_targets_national.csv) were strictly mass-conserved ($\sum T = 1.0000$), the time-aggregated matrix in [`transport_matrix_national.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/national_pilot/transport_matrix_national.csv) exhibited inflated fractions, with row sums reaching up to **$16.0225$**.

### Root Cause Identification:
* **The Sparse-Filtering Omission:** In `physics_2d_national_dispersion.py`, `df_out` only records destination cells that received $>0$ ensemble particles at timestamp $t$.
* **The Flawed Aggregation:** The code grouped `df_out` by `(station_id, dest_grid_id, elapsed_time_hours)` and applied `.agg(mean_transport_fraction=("transport_fraction", "mean"))`.
* **Mathematical Consequence:** Pandas computed the mean across **only the active time steps where that destination was visited** ($N_{\text{visited}}$), omitting all valid simulation steps where zero particles were transported to that cell ($T = 0$):
  $$\bar{T}_{\text{flawed}} = \frac{1}{N_{\text{visited}}} \sum_{t \in \text{Visited}} T(src, dest, t, \Delta t) \quad \text{where } N_{\text{visited}} \le N_{\text{eligible}}$$
* **The Fix:** For any destination cell $j$, the true unconditional time-average transport probability over an analysis window must divide by the total number of **eligible simulation time steps** ($N_{\text{eligible}}$):
  $$\bar{T}_{ij}(\Delta t) = \frac{1}{N_{\text{eligible}}(i, \Delta t)} \sum_{t \in \mathcal{E}(i, \Delta t)} T_{ij}(t, \Delta t)$$

---

## 2. Preservation of Baselines & Versioning Integrity

In strict accordance with preservation rules:
1. **Pre-Change Script Preserved:** Saved exact pre-change implementation to [`src/national/physics_2d_national_dispersion_pre_phase10_backup.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/src/national/physics_2d_national_dispersion_pre_phase10_backup.py).
2. **Phase 8 Results Untouched:** All files in [`results/national_pilot/`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/national_pilot/) (`transport_targets_national.csv`, `transport_matrix_national.csv`, `boundary_loss_statistics_national.csv`, `national_constraints_report.csv`, figures) remain completely unaltered.
3. **Synthetic, Regional & Seasonal Baselines Untouched:** `data/synthetic/`, `data/regional/`, `results/regional_pilot/`, and `results/regional_seasonal_winter/` are confirmed identical.
4. **Corrected Outputs Versioned:** Written to an isolated directory: [`results/phase10_matrix_fix/`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase10_matrix_fix/).

---

## 3. Mathematical Formulation of the Minimal Correction

Let:
* $\mathcal{E}(i, \Delta t)$ be the set of valid, completed simulation steps for source station $i$ and advection window $\Delta t$.
* $N_{\text{eligible}}(i, \Delta t) = |\mathcal{E}(i, \Delta t)|$ be the count of eligible steps.
* $T_{ij}(t, \Delta t)$ be the instantaneous endpoint fraction of $N=20$ trajectories residing in destination cell $j$ at time step $t$.

### Inside-Domain Cells ($j \in \text{Domain}$):
$$\bar{T}_{ij}(\Delta t) = \frac{\sum_{t \in \mathcal{E}(i, \Delta t)} T_{ij}(t, \Delta t)}{N_{\text{eligible}}(i, \Delta t)}$$
$$\bar{I}_{ij}(\Delta t) = \frac{\sum_{t \in \mathcal{E}(i, \Delta t)} I_{ij}(t, \Delta t)}{N_{\text{eligible}}(i, \Delta t)}$$

### Outside-Domain Sinks ($j = \text{OUTSIDE\_DOMAIN}$):
$$\bar{T}_{i, \text{outside}}(\Delta t) = \frac{\sum_{t \in \mathcal{E}(i, \Delta t)} \text{boundary\_loss\_fraction}(i, t, \Delta t)}{N_{\text{eligible}}(i, \Delta t)}$$

### Mathematical Proof of Strict Closure:
$$\sum_{j \in \text{Domain}} \bar{T}_{ij}(\Delta t) + \bar{T}_{i, \text{outside}}(\Delta t) = \frac{1}{N_{\text{eligible}}} \left[ \sum_{t \in \mathcal{E}} \left( \sum_{j \in \text{Domain}} T_{ij}(t) + T_{\text{outside}}(t) \right) \right]$$
Since for every individual synoptic step $t$, the term in brackets is strictly $1.0000$:
$$= \frac{1}{N_{\text{eligible}}} \sum_{t \in \mathcal{E}} 1.0000 = \frac{N_{\text{eligible}}}{N_{\text{eligible}}} = \mathbf{1.0000000000000000 \quad \text{EXACTLY!}}$$

---

## 4. Old vs Corrected Aggregation Comparison

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                    AGGREGATION COMPARISON TABLE (OLD VS CORRECTED)                                    |
+---------------+-------------------+---------------+------+-------+-------+------------+------------+------------------+
| Station City  | Station Name      | Dest Grid ID  | dt   | N_vis | N_elg | Old Mean T | New Mean T | Inflation Factor |
+---------------+-------------------+---------------+------+-------+-------+------------+------------+------------------+
| Kanpur        | FTI Kidwai Nagar  | IND_r054_c038 | 24h  | 1     | 28    | 0.050000   | 0.001786   | 28.00x (Infreq)  |
| Guwahati      | Pan Bazaar        | IND_r048_c096 | 6h   | 1     | 28    | 0.050000   | 0.001786   | 28.00x (Infreq)  |
| Agra          | Sector-3B Avas    | IND_r043_c041 | 12h  | 2     | 28    | 0.050000   | 0.003571   | 14.00x           |
| Varanasi      | Bhelupur          | IND_r051_c061 | 6h   | 7     | 28    | 0.078571   | 0.019643   | 4.00x            |
| Prayagraj     | Jhunsi            | IND_r050_c057 | 3h   | 13    | 26    | 0.138462   | 0.069231   | 2.00x            |
| Guwahati      | Pan Bazaar        | IND_r047_c095 | 3h   | 27    | 28    | 0.653704   | 0.630357   | 1.04x            |
| Ahmedabad     | SVPI Airport      | IND_r060_c019 | 1h   | 27    | 27    | 1.000000   | 1.000000   | 1.00x (Home Cell)|
+---------------+-------------------+---------------+------+-------+-------+------------+------------+------------------+
```
* **Key Finding:**  
  * For home cells at $dt=1\text{h}$ visited in 100% of time steps ($N_{\text{vis}} = N_{\text{elg}}$), the old and corrected values are **identical** (inflation = $1.00\times$).  
  * For distant, peripheral cells visited in only 1 of 28 steps, the old matrix inflated the fraction by exactly $N_{\text{elg}} / N_{\text{vis}} = 28.0\times$!  
  * The corrected matrix suppresses these rare occurrences to their true climatological probability ($0.05 / 28 = 0.001786$), restoring exact physical proportionality.

---

## 5. Closure Statistics: Before vs After Correction

```
+----------------------------------------------------------------------------------------------------+
|                                    CLOSURE METRICS AUDIT TABLE                                     |
+------------------------------------+--------------------------+------------------------------------+
| Metric                             | Old Phase 8 Matrix       | Phase 10 Corrected Matrix          |
+------------------------------------+--------------------------+------------------------------------+
| Minimum Row Sum                    | 1.000000 (at dt=1h)      | 1.0000000000000000                 |
| Maximum Row Sum                    | 16.022500 (at dt=24h)    | 1.0000000000000000                 |
| Mean Row Sum                       | 6.275900                 | 1.0000000000000000                 |
| Maximum Absolute Closure Error     | +15.022500 (1,502% error)| 1.11 x 10^-16 (Machine Epsilon)    |
| Total Source-Window Pairs Audited  | 50 combinations          | 50 combinations                    |
| Closure Compliance Rate            | 20.0% (10 of 50 passed)  | 100.0% (50 of 50 passed)           |
+------------------------------------+--------------------------+------------------------------------+
```
*Full audit available at:* [`results/phase10_matrix_fix/transport_matrix_closure_audit.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase10_matrix_fix/transport_matrix_closure_audit.csv).

---

## 6. Regression Test Suite Execution (7 of 7 Passed)

All 7 required regression tests were executed deterministically:

```
+--------------------------------------------------------------------------------------------------------------------+
|                                      PHASE 10 REGRESSION TEST RESULTS REGISTRY                                     |
+-----+-----------------------+---------------------------------------+--------------------+----------------+--------+
| ID  | Test Name             | Description                           | Tolerance          | Measured Metric| Status |
+-----+-----------------------+---------------------------------------+--------------------+----------------+--------+
| T_A | Matrix Closure        | Sum of inside fractions + outside ==1 | Max error < 1e-5   | Max err=1.1e-16| PASS   |
| T_B | Zero-Transport Steps  | Deterministic 4-step multi-dest test  | Exact match        | Sum = 1.0000   | PASS   |
| T_C | Missing-Data Handling | Invalid steps excluded from N_eligible| N_elg = 26 (not 28)| 26 eligible    | PASS   |
| T_D | Boundary Accounting   | Outside fraction divided by N_eligible| Symmetrical closure| Closure=1.00000| PASS   |
| T_E | Reproducibility       | Two independent runs match bitwise    | SHA-256 identical  | a5d4a176baaf...| PASS   |
| T_F | Physics Regression    | Per-step transport records untouched  | Rows=7730, T=1335.0| Exact match    | PASS   |
| T_G | Count & Bound Bounds  | 2,831 pairs, zero duplicates, [0, 1]  | Dups=0, NaNs=0     | Zero dups/NaNs | PASS   |
+-----+-----------------------+---------------------------------------+--------------------+----------------+--------+
| OVERALL SCORE: 7 OF 7 REGRESSION TESTS PASSED (100.0%)                                                             |
+--------------------------------------------------------------------------------------------------------------------+
```
*Full test registry available at:* [`results/phase10_matrix_fix/regression_test_results.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase10_matrix_fix/regression_test_results.csv).

---

## 7. Remaining Scientific Limitations

1. **Station Density:** Active pilot monitoring is currently concentrated in 10 urban monitoring centers across 7 cities. Rural receptor grids between urban corridors lack in-situ ground validation monitors.
2. **2D Kinematic Simplification:** Advection is governed by ERA5 $10\text{-meter}$ surface wind fields ($U_{10}, V_{10}$). The model does not resolve vertical wind shear, boundary-layer entrainment, or wet/dry aerosol deposition.
3. **Derived Quantities:** The metric $I = \text{PM}_{2.5}^{\text{src}} \times \bar{T}$ represents potential source-weighted transport contribution. It must **never** be interpreted as ambient air quality index (AQI) forecasting.

---

## 8. Final Decision & Next Phase Authorization

### **DECISION: GO FOR PRODUCTION PREPARATION**

* The matrix time-aggregation defect has been **completely resolved**.
* Numerical closure is verified to within **$1.11 \times 10^{-16}$** across all source stations and advection windows.
* All underlying Lagrangian physics, particle trajectories, ensemble configurations, and baseline outputs remain **100% preserved and regression-verified**.
* The national dispersion modeling system is now ready for production batch scaling across annual and seasonal historical datasets.
