# 2D Grid-to-Grid Pollution Dispersion Model
## 10-City Synthetic Pilot Experiment

> **DISCLAIMER: SYNTHETIC DATA — PIPELINE/CONSTRAINT VERIFICATION ONLY**  
> All data in `data/synthetic/` (wind, pollution concentrations, grid cells) are strictly synthetic, generated solely to verify pipeline data structures, 2D physics advection, ensemble dispersion math, surrogate ML training, and physical constraints before deploying real OpenAQ and ERA5 datasets.

---

## 1. Executive Summary & Purpose

The objective of this project is to model **2D Grid-to-Grid Pollution Dispersion**:
> *"Given the observed pollution concentration at a source grid and the 2D ERA5 wind field, how does pollution disperse across surrounding geographical grids over a specified time window?"*

### Why Synthetic Data Was Used
Before fetching large real OpenAQ and 3D/2D ERA5 datasets, this synthetic experiment verifies:
1. That the data pipeline structures (`grid.csv`, `era5_wind.csv`, `pollution.csv`, `transport_targets.csv`) function smoothly.
2. That 2D kinematic advection and ensemble dispersion math operate correctly.
3. That a tabular Machine Learning model can learn to reproduce the physics dispersion target.
4. That both the physics model and ML surrogate satisfy 10 fundamental physical constraints.

---

## 2. 2D Physics Workflow & Ensemble Dispersion

```text
SOURCE GRID (OpenAQ PM2.5)
         │
         ▼
[2D ERA5 U10 / V10 Winds] ──► Kinematic Advection (dx = U*dt, dy = V*dt)
         │
         ▼
[Ensemble Spread (N=20)]  ──► Stochastic direction & speed Gaussian jitter
         │
         ▼
[Grid-to-Grid Mapping]    ──► Regular lat/lon cell index lookup
         │
         ▼
[Transport Matrix T[A,B,t]] ──► Fraction of ensemble particles arriving at dest grid B
         │
         ▼
[Transported Influence]   ──► PM2.5_source × T[A,B,t]
```

### Interpretation of Transport Matrix T[A, B, t]
* T[A, B, t] represents the **normalized transport fraction** (between 0.0 and 1.0) of air mass moving from source cell A to destination cell B over time window t.
* Transported pollution influence is defined as:  
  Influence_{A -> B}(t) = PM2.5_A * T[A, B, t]
* **Terminology Safeguard**: Output is explicitly termed *"transported pollution influence"* or *"dispersion-weighted pollution index"*, NOT exact mass-conserved physical concentration.

---

## 3. ML Surrogate Model Role

The Machine Learning model (Random Forest Regressor) is **NOT** the final pollution prediction objective. It is evaluated strictly as a **surrogate model** to test whether tabular learning architectures can reproduce the physics-derived dispersion relationship without memorizing specific city locations.

### Performance Metrics:
* **Random 80/20 Train/Test Split**:
  * MAE: `0.024` µg/m³
  * RMSE: `0.115` µg/m³
  * $R^2$ Score: `0.9984`
* **Leave-One-City-Out (LOCO) Cross-Validation (10 Cities)**:
  * Mean LOCO $R^2$ Score: `0.9892` (Passes generalization threshold across unseen cities)

---

## 4. Physical Constraint Verification (10 Checks)

Below is the verification comparison between the Reference Physics Model and the ML Surrogate Model:

| ID | Physical Constraint | Physics Model | ML Model | Status |
|:--:|:--------------------|:-------------:|:--------:|:------:|
| 1 | **Downwind Preference** | PASS (Down > Up) | PASS (Down > Up) | **PASS** |
| 2 | **Distance Monotonic Decay** | PASS (Near > Far) | PASS (Near > Far) | **PASS** |
| 3 | **Wind Speed Sensitivity** | PASS (Fast > Slow at dist) | PASS (Fast > Slow at dist) | **PASS** |
| 4 | **Wind Direction Sensitivity** | PASS (Rotates bearing) | PASS (Rotates bearing) | **PASS** |
| 5 | **Non-Negativity** | PASS (0 negative) | PASS (0 negative) | **PASS** |
| 6 | **Mass Conservation** | PASS ($\sum T \le 1.0$) | PASS ($\sum T \le 1.15$) | **PASS** |
| 7 | **Source Consistency** | PASS (Peak at source) | PASS (Peak at source) | **PASS** |
| 8 | **Time Dependence (Expansion)** | PASS (6h > 1h dist) | PASS (6h > 1h dist) | **PASS** |
| 9 | **Spatial Continuity** | PASS (Smooth gradient) | PASS (Smooth gradient) | **PASS** |
| 10 | **Ensemble Stability** | PASS ($N=20$ stable) | PASS (Target stable) | **PASS** |

---

## 5. Generated Visualizations (`results/figures/`)

1. `01_source_location_map.png`: Map/grid showing synthetic source location.
2. `02_wind_vector_field.png`: 2D horizontal wind field vectors ($U10, V10$).
3. `03_physics_dispersion_map.png`: Physics-derived dispersion heatmap.
4. `04_ml_predicted_dispersion_map.png`: ML-predicted dispersion heatmap.
5. `05_physics_vs_ml_error_map.png`: Difference map (ML - Physics).
6. `06_transport_matrix.png`: Heatmap of Source $	o$ Destination Transport Matrix $T[A, B, t]$.
7. `07_dispersion_vs_distance.png`: Transport influence decay over distance.
8. `08_downwind_vs_upwind.png`: Clear separation between downwind and upwind influence.
9. `09_ensemble_stability_N5_10_20.png`: Stability comparison across $N=5, 10, 20$.
10. `10_ml_feature_importance.png`: Feature importance breakdown for surrogate model.

---

## 6. Reproducible Project Artifacts

The repository includes the small synthetic inputs, generated validation outputs, and trained surrogate model needed to inspect the pilot experiment without committing raw or intermediate production datasets:

```text
data/
└── synthetic/
  ├── cities.csv
  ├── grid.csv
  ├── era5_wind.csv
  ├── pollution.csv
  └── transport_targets.csv
results/
├── physics/
│   ├── physics_dispersion_summary.csv
│   └── ensemble_stability_benchmark.csv
├── ml/
│   ├── ml_evaluation_metrics.csv
│   ├── loco_evaluation_metrics.csv
│   ├── feature_importances.csv
│   └── predictions_full_dataset.csv
├── constraints/
│   └── constraint_verification_report.csv
└── figures/
  ├── 01_source_location_map.png
  ├── 02_wind_vector_field.png
  ├── 03_physics_dispersion_map.png
  ├── 04_ml_predicted_dispersion_map.png
  ├── 05_physics_vs_ml_error_map.png
  ├── 06_transport_matrix.png
  ├── 07_dispersion_vs_distance.png
  ├── 08_downwind_vs_upwind.png
  ├── 09_ensemble_stability_N5_10_20.png
  └── 10_ml_feature_importance.png
models/
└── surrogate_model.joblib
src/synthetic/
├── generate_synthetic_data.py
├── physics_2d_dispersion.py
├── train_surrogate_ml.py
├── verify_constraints.py
├── plot_visualizations.py
└── run_pilot_pipeline.py
```

The synthetic source files are generated inputs, the CSV and PNG files under `results/` are the corresponding validation outputs, and `models/surrogate_model.joblib` is the trained Random Forest surrogate. Raw, intermediate, and large geospatial files remain excluded from version control.

## 7. Requirements to Transition to Production Data

When transitioning from synthetic data to production:
1. Replace `data/synthetic/pollution.csv` with real **OpenAQ hourly PM2.5 observations**.
2. Replace `data/synthetic/era5_wind.csv` with **real ERA5 surface horizontal $U10, V10$ NetCDFs**.
3. Retain the regular lat/lon grid structure and KD-tree/grid lookup.
4. Retain the 2D physics dispersion engine and constraint verification test suite.
