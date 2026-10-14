# Phase 12 — Task 1: Independent Reproducibility Audit Report

## 1. Executive Summary

Every single reported count, timestamp range, execution slice, and dataset dimension from Phase 11 was **100% independently reproduced and confirmed to be internally consistent**.

## 2. Quantitative Counts Verification Table

| Metric / Parameter | Phase 11 Reported | Phase 12 Audited | Exact Match? |
|---|---|---|:---:|
| Temporal Start | `2021-09-15 00:00:00` | `2021-09-15 00:00:00` | **PASSED** |
| Temporal End | `2021-10-20 18:00:00` | `2021-10-20 18:00:00` | **PASSED** |
| Synoptic Step Count | `144` | `144` | **PASSED** |
| Station Count | `10` | `10` | **PASSED** |
| Total Station-Step Slots | `1440` | `1440` | **PASSED** |
| Executed Slices (Valid PM2.5 + Wind) | `847` | `847` | **PASSED** |
| Unmonitored Slices (Missing PM2.5) | `593` | `593` | **PASSED** |
| Missing Meteorology Slices | `0` | `0` | **PASSED** |
| Aligned In-situ Slices | `847` | `847` | **PASSED** |
| Total Simulation Runs | `4235` | `4235` | **PASSED** |
| Elapsed Windows Evaluated | `1, 3, 6, 12, 24` | `[np.float64(1.0), np.float64(3.0), np.float64(6.0), np.float64(12.0), np.float64(24.0)]` | **PASSED** |
| Ensemble Size (N) | `20` | `20` | **PASSED** |
| Transport Target Records | `25864` | `25864` | **PASSED** |
| Aggregated Matrix Pairs | `7243` | `7243` | **PASSED** |
| Closure Groups (Station x Window) | `50` | `50` | **PASSED** |
| Transport Skipped on Missing PM2.5 | `Yes (coupled)` | `Yes (coupled)` | **PASSED** |

## 3. Structural Analysis: Coupling of Missing PM2.5 and Transport Simulations

An in-depth code inspection of `src/phase11_validation/run_multiweek_dispersion.py` was conducted to determine how missing ground observations were handled:

```python
if len(st_obs_row) == 0:
    run_log.append({
        'timestamp_utc': t_str,
        'station_id': s_id,
        'status': 'EXCLUDED_NO_GROUND_OBSERVATION',
        'details': 'Station offline, in maintenance, or no valid PM2.5 readings within +/-1h synoptic window'
    })
    continue  # <--- Skips 2D Lagrangian ensemble advection
```

### Key Findings:
1. **Missing Data Was NOT Fabricated**: No missing observation was replaced with zero concentration. Missing ground data was transparently logged and excluded.
2. **Coupled vs Uncoupled Architecture**:
   - **In Phase 11**: The physical advection engine was executed *conditionally* on the presence of a valid ground PM2.5 reading. When a station was unmonitored (593 slices), no Lagrangian trajectories were computed, even though valid ERA5 winds existed.
   - **Scientific Assessment**: The kinematic transport probability $\bar{T}_{i \to j}(\Delta t)$ is fundamentally a meteorological Green's function that depends solely on the wind field, not on ground sensor operations. Coupling transport calculation to sensor uptime means that $\bar{T}$ is only sampled over sensor-active periods.
   - **Impact**: For source-influence calculations ($I = \text{PM}_{2.5}^{\text{src}} \times \bar{T}$), this coupling is mathematically required because source concentration cannot be multiplied by an unmeasured value. However, for annual production, a pure meteorological transport matrix can be computed across all valid ERA5 timestamps ($100\%$ sampling), while concentration weighting should be applied separately where observations exist.
