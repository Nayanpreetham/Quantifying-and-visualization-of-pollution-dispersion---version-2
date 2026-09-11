# Current System Audit
*Generated: 2026-09-11 — Verified against actual code, not documentation*

---

## 1. Verified Implementations

### 1.1 Meteorological Forcing
| Item | Status | Notes |
|---|---|---|
| ERA5 surface (u10, v10, t2m, blh, sp) | IMPLEMENTED | Processed to derived vars in meteorology.py |
| ERA5 3D pressure-level (u, v, w at 5 levels) | IMPLEMENTED (pilot only) | era5_3d_2020_11_01.nc, Oct-Nov 2020, 3-hourly |
| ERA5 2020-2024 annual files | FILES EXIST | Not yet preprocessed per-month for batch |
| Surface pressure sp for terrain masking | IMPLEMENTED | Used in 3D engine for underground clamping |

### 1.2 3D RK4 Trajectory Engine (trajectory_model_3d.py)
| Item | Status | Notes |
|---|---|---|
| RK4 integration in pressure coordinates | IMPLEMENTED | Correct 4-stage algorithm |
| scipy RegularGridInterpolator for 4D fields | IMPLEMENTED | Fast in-memory interpolation |
| Backward sign convention (-u, -v, -omega) | IMPLEMENTED | Correct for backward trajectories |
| AGL to hPa conversion | WRONG | Uses p = sp - h/8 hardcoded approximation, not ISA |
| ISA atmosphere.py | IMPLEMENTED | But NOT connected to ensemble AGL conversion |
| Upper pressure cap at 500 hPa | HARDCODED | No physical justification; reflects trajectories |
| ASL altitude in trajectory output | MISSING | pressure_hpa recorded but not altitude_asl |
| Omega units | CORRECT | w in Pa/s divided by 100 to get hPa/s |

### 1.3 Ensemble Model (ensemble_model.py)
| Item | Status | Notes |
|---|---|---|
| EnsembleTrajectoryModel class | IMPLEMENTED | 5 spatial x 4 vertical = up to 20 members |
| Horizontal perturbations +/-10 km | IMPLEMENTED | North/South/East/West/Center |
| Vertical levels 50/100/300/500 m AGL | IMPLEMENTED | Uses wrong sp-h/8 approximation |
| Stochastic turbulent perturbations | NOT IMPLEMENTED | Only initial-condition spread |
| Ensemble stability diagnostics | SCRIPT EXISTS | Never successfully executed |

### 1.4 Source-Grid Intersection (source_receptor.py)
| Item | Status | Notes |
|---|---|---|
| 50-km grid (4209 cells) | EXISTS | india_50km_grid.geojson |
| Trajectory-to-grid sjoin | IMPLEMENTED | geopandas sjoin, very slow |
| Transport weight = residence_points / total_points | IMPLEMENTED | Fraction of ALL points in each cell |
| Country/ocean classification | IMPLEMENTED | Downloads world.geo.json at runtime |
| frac_outside_domain | IMPLEMENTED | Points not in any 50-km cell |
| calculate_trajectory_influence (old function) | DELETED BUT REFERENCED | Breaks run_historical_batch.py and test_trajectory_convergence.py |

### 1.5 Source-Influence Calculation
| Item | Status | Notes |
|---|---|---|
| transport_weighting.py | STALE | Column schema mismatches ensemble output; crashes if called |
| contribution.py | STALE | References Kljun footprint columns not produced by ensemble |
| Seasonal modifier S_i | HARDCODED 1.0 | Diwali gets 1.5, no other logic |
| Sinusoidal periodic disturbance | NOT IMPLEMENTED | Referenced in methodology but absent from all code |
| Source categories (power/industry/transport) | NOT IMPLEMENTED | No data, no interface |
| Emissions inventory | NOT IMPLEMENTED | No spatial emissions data of any kind |

### 1.6 Observed Pollution Data
| Item | Status | Notes |
|---|---|---|
| CPCB AQI bulletin CSVs | 277 CITY FILES | Daily city-level AQI index only, no lat/lon, no PM2.5 in ug/m3 |
| OpenAQ station metadata | 759 STATIONS | 573 CPCB-sourced, metadata only |
| Actual PM2.5 measurements | NOT FETCHED | cpcb_nov2020.py references file that does not exist |
| cpcb.py download | MOCK DATA ONLY | Returns 2 hardcoded rows |
| Grid-aggregated AQI field | 1 TIMESTAMP | aggregated_50km_20201101_120000.csv from kriging of bulletin AQI |

### 1.7 Validation
| Item | Status | Notes |
|---|---|---|
| 10-city pilot script | WRITTEN | Never successfully completed |
| Correlation/RMSE/MAE vs observations | NOT IMPLEMENTED | No code exists |
| Temporal split validation | NOT IMPLEMENTED | |

### 1.8 Historical Batch
| Item | Status | Notes |
|---|---|---|
| run_historical_batch.py | TEMPLATE ONLY | ERA5 download commented out; breaks immediately |
| 3D ERA5 for 2021-2024 | NOT DOWNLOADED | Only 2 months available |

---

## 2. Scientific Honesty Statement

The current system solves ATMOSPHERIC TRANSPORT PATHWAY INFLUENCE only.

It does NOT currently solve:
- Source attribution (requires emissions inventory)
- PM2.5 concentration prediction (requires measured PM2.5, not AQI index)
- Periodic disturbance representation (not implemented)
- Source-category influence (no data)
- Quantitative validation (never executed)
- Historical India-wide analysis (insufficient 3D ERA5 data)

## 3. Broken References

1. run_historical_batch.py imports calculate_trajectory_influence - function deleted
2. tests/test_trajectory_convergence.py imports calculate_trajectory_influence - fails on import
3. transport_weighting.py and contribution.py have incompatible column schemas with ensemble output
4. experiment_validation_pilot.py performance bottleneck: never completes
