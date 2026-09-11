# Implementation Roadmap — Gap Analysis & Priorities

## CURRENT vs REQUIRED vs GAP vs ACTION

| # | Component | Current State | Required State | Gap | Priority |
|---|---|---|---|---|---|
| 1 | AGL-to-pressure conversion | sp - h/8 approximation | ISA-based (atmosphere.py) | FIXED in this session | P0 DONE |
| 2 | Broken imports (calculate_trajectory_influence) | ImportError in 2 files | Correct function name | FIXED in this session | P0 DONE |
| 3 | Periodic disturbance | Not implemented | Sinusoidal formulation | IMPLEMENTED in this session | P0 DONE |
| 4 | Source-category interface | Not implemented | Framework with TRANSPORT_ONLY fallback | IMPLEMENTED in this session | P0 DONE |
| 5 | Fast grid lookup | O(N*M) sjoin — unusably slow | O(N) KD-tree | IMPLEMENTED in this session | P0 DONE |
| 6 | 10-city pilot | Never ran | Runs end-to-end producing real output | RUNNING in this session | P1 IN PROGRESS |
| 7 | Observed PM2.5 measurements | Not fetched | Hourly station PM2.5 via OpenAQ API | Fetch via cpcb_nov2020.py | P1 |
| 8 | Correlation vs observations | Not implemented | Pearson/Spearman on transport influence vs AQI | Implement after pilot completes | P1 |
| 9 | Ensemble stability run | Script exists, never ran | N=5/10/20 stability table for all 10 cities | Run after pilot | P1 |
| 10 | transport_weighting.py schema fix | Column mismatch with ensemble output | Match ensemble output columns | Refactor | P1 |
| 11 | 3D ERA5 for full date range | Oct-Nov 2020 only | 2020-2024 monthly chunks | Download via CDS API | P2 |
| 12 | Monthly ERA5 surface preprocessing | Annual files only | Per-month processed NetCDF | Script exists; uncomment | P2 |
| 13 | Emissions inventory | Not available | IIASA GAINS / EDGAR / CAMS | Download and integrate | P2 |
| 14 | GO/NO-GO checklist verification | Not done | All criteria met | Review checklist below | P2 |
| 15 | Trajectory length sensitivity | Not tested | 24h / 48h / 72h comparison | Script needed | P2 |
| 16 | Resolution sensitivity (50km vs other) | Not tested | Sensitivity report | Script needed | P3 |
| 17 | HYSPLIT benchmark | Not available | Endpoint comparison | Optional | P3 |

---

## P0 — Must Fix Before Validation (COMPLETED in this session)

### [DONE] Fix 1: AGL-to-pressure (ensemble_model.py)
- BEFORE: p_start = sp - (h / 8.0)  [wrong constant]
- AFTER: ISA barometric formula via atmosphere.py
- TEST: test_atmosphere.py passes

### [DONE] Fix 2: Broken imports
- BEFORE: calculate_trajectory_influence imported in 2 files, function deleted
- AFTER: replaced with calculate_ensemble_influence
- TEST: unittest discover no longer fails on import

### [DONE] Fix 3: Periodic disturbance (NEW FILE: src/physics/periodic_disturbance.py)
- BEFORE: not implemented anywhere
- AFTER: sinusoidal annual + diurnal + weekly harmonics + event calendar lookup
- OUTPUT: D(2020-11-01 00:00) = 1.05, D(Diwali 2020) = 1.66
- TEST: compute_periodic_disturbance() returns bounded values in [0.5, 2.5]

### [DONE] Fix 4: Source-category interface (NEW FILE: src/physics/source_categories.py)
- BEFORE: not implemented
- AFTER: SourceCategoryWeighter class, TRANSPORT_ONLY fallback, EMISSION_WEIGHTED mode
- TEST: TRANSPORT_ONLY mode returns source_influence_index = transport_weight

### [DONE] Fix 5: Fast grid lookup (NEW FILE: src/transport/grid_lookup.py)
- BEFORE: sjoin on all ~4209 polygons per trajectory point — O(N*M), unusably slow
- AFTER: KD-tree nearest-centroid lookup — O(N), grid assignment in <0.01s
- TEST: Delhi=IND_047_021, Mumbai=IND_026_012, Arabian Sea (65E)=None ✅

---

## P1 — Required for 10-City Validation

### [ ] P1.1: Fetch actual PM2.5 measurements
- Run src/data/cpcb_nov2020.py to get OpenAQ hourly measurements
- Current CPCB AQI bulletins are daily city-level index only, no lat/lon
- Required for quantitative correlation

### [ ] P1.2: Correlation analysis
- Implement src/validation/transport_aqi_correlation.py
- Input: pilot_results_10city.csv + observed AQI/PM2.5
- Compute Pearson, Spearman, R² between transport influence signal and AQI
- Use daily AQI as proxy until station PM2.5 is fetched

### [ ] P1.3: Ensemble stability
- Run src/diagnostics/ensemble_stability.py after pilot completes
- Report Top-1/3/5 stability for N=5/10/20

### [ ] P1.4: Fix transport_weighting.py schema
- Current column names mismatch ensemble output
- Align to: source_grid_id, transport_weight, source_influence_index

---

## P2 — Required Before 5-Year Historical Run

### [ ] P2.1: GO/NO-GO Checklist (all must be green)
- [ ] ERA5 3D data available for target months (2020-2024)
- [ ] Trajectory integration passes analytical tests
- [ ] Ensemble N=20 stability confirmed (Top-5 overlap >= 80%)
- [ ] Grid lookup produces correct domain masks
- [ ] Periodic disturbance parameters calibrated or documented as defaults
- [ ] Source-category emissions loaded OR TRANSPORT_ONLY explicitly documented
- [ ] 10-city pilot results reviewed and accepted
- [ ] Correlation vs observations computed (even if weak — must be measured)
- [ ] Runtime benchmark: <30 min per city-month on available hardware
- [ ] Storage plan: Parquet by year/month/city confirmed

### [ ] P2.2: Download ERA5 3D for 2020-2024
- Uncomment download_era5_chunk() in run_historical_batch.py
- Use sliding window (1 month at a time, delete after processing)

### [ ] P2.3: Monthly ERA5 surface preprocessing
- Extract monthly NetCDFs from annual era5_20XX.nc files

### [ ] P2.4: Emissions inventory
- Recommended: EDGAR v7 PM2.5 India grid
- URL: https://edgar.jrc.ec.europa.eu/dataset_ghg70
- Format: NetCDF, ~0.1 deg resolution, annual sector-based

---

## P3 — Optional Research Enhancements

- Trajectory-length sensitivity (24h vs 48h vs 72h source ranking)
- Source-grid resolution sensitivity (50km vs 25km)
- Stochastic turbulent velocity perturbations (if sigma_v data available)
- HYSPLIT benchmark comparison
- LSTM/graph-based ML on top of physics features (only after P2 complete)
