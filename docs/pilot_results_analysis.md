# 10-City Pilot Results
*Generated: 2026-09-11 | ERA5 pilot window: 2020-11-01 | Mode: TRANSPORT_ONLY*

---

## Summary Table

| City | Observed AQI | N Members | Avg Source Cells | Avg D(t) | Outside Domain |
|---|---|---|---|---|---|
| Kanpur   | 360 | 20 | 50 | 1.12 | 0% |
| Lucknow  | 291 | 20 | 56 | 1.12 | 0% |
| Delhi    | 288 | 20 | 46 | 1.12 | 0% |
| Varanasi | 263 | 20 | 39 | 1.12 | 0% |
| Patna    | 164 | 20 | 53 | 1.12 | 0% |
| Hyderabad| 152 | 20 | 76 | 1.12 | 0% |
| Kolkata  | 152 | 20 |  9 | 1.12 | 0% |
| Mumbai   | 111 | 20 | 68 | 1.12 | 0% |
| Ahmedabad| 101 | 20 | 73 | 1.12 | 0% |
| Bengaluru|  67 | 20 |  1 | 1.12 | 0% |

---

## Scientific Findings

### 1. IGP Corridor (Delhi, Lucknow, Varanasi, Kanpur, Patna)

All five IGP cities show AQI > 160. Trajectories remain fully within India
(0% outside-domain fraction), consistent with the stagnant high-pressure
systems that trap pollution in the Indo-Gangetic Plain during post-monsoon season.

Source cells for Delhi at 00:00 UTC are shifted northwest (IND_060_XXX —
approximately Rajasthan/Haryana region), consistent with northeast wind direction
in November (anticyclonic flow brings Rajasthan dust and regional pollution).

### 2. Coastal Cities (Mumbai, Kolkata)

Mumbai (AQI=111): trajectories span 61-75 source cells, indicating active
sea-breeze circulation disperses air mass over a large area. Top source cells
are in the Maharashtra coastal zone, as expected.

Kolkata (AQI=152): very few source cells (9), suggesting the air mass
remains highly local. This is consistent with low-wind conditions at the
Bay of Bengal shore in November.

### 3. Southern and Western Cities

Hyderabad (AQI=152): trajectories spread across 69-82 cells, consistent
with the Deccan Plateau being exposed to multiple flow regimes.

Ahmedabad (AQI=101): 66-80 source cells, with top influence from cells
to the north/northeast (Rajasthan corridor).

### 4. Bengaluru Anomaly — OUT-OF-DOMAIN ERA5

**FINDING**: Bengaluru (lat=12.97°N) is OUTSIDE the 3D ERA5 domain
(which was downloaded for 15-35°N, 68-90°E). Therefore:
- `interp_sp()` returns the fill_value (101325 Pa)
- `_get_interpolated_wind()` returns zeros on all pressure levels
- Trajectory breaks at first step: all 20 members stall at the release point
- Result: top1_source = Bengaluru's own cell, transport_weight = 1.0

**This is not a bug in the trajectory model. It is a data domain limitation.**

**Action Required**: When downloading 3D ERA5 for production, extend the
latitude domain to 5-38°N to cover all Indian cities including Chennai,
Thiruvananthapuram, and Bengaluru.

---

## Periodic Disturbance

D(2020-11-01 00:00 UTC) = 1.051
D(2020-11-01 12:00 UTC) = 1.181

The higher D at 12:00 UTC reflects the diurnal component peaking in the
afternoon (India time ~17:30 IST = 12:00 UTC), consistent with increased
traffic and boundary-layer mixing.

D is UNIFORM across source cells at each timestamp — it modulates overall
signal magnitude, not the spatial source ranking.

---

## GO / NO-GO Status

| Criterion | Status |
|---|---|
| RK4 trajectory integration passes analytical tests | PASS |
| 20-member ensemble runs for all cities in domain | PASS |
| Grid assignment fast (<0.01s per trajectory set) | PASS |
| Periodic disturbance D(t) computed and bounded | PASS |
| Source-category interface ready for emissions data | PASS |
| 10-city pilot completes without crash | PASS |
| Bengaluru ERA5 domain gap documented | DOCUMENTED |
| Correlation vs observed AQI computed | NOT YET |
| Ensemble stability N=5/10/20 tested | NOT YET |
| 3D ERA5 domain extended to 5-38°N | NOT YET (P2) |
| Emissions inventory loaded | NOT YET (P2) |

**Current recommendation**: DO NOT start 5-year batch.
**Next step**: Run ensemble stability check, fetch PM2.5 measurements, extend ERA5 domain.
