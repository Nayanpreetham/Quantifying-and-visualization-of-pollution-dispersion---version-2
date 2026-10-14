# Phase 9 — Task 3: Grid Indexing & Particle Movement Audit

**Audit Timestamp:** 2026-10-14 22:38 UTC  
**Overall Status:** 28 of 28 Unit Tests Passed (100.0%)  

---

## 1. Mapping Semantics: Nearest Node vs Containing Cell

The function `map_particle_to_national_grid` operates via rounding:  
$$\text{row} = \text{int}\left(\text{round}\left(\frac{38.0 - \text{lat}}{0.25}\right)\right), \quad \text{col} = \text{int}\left(\text{round}\left(\frac{\text{lon} - 68.0}{0.25}\right)\right)$$

- **Behavior:** This maps any coordinate $(lat, lon)$ to its **nearest regular grid node center** within a square Voronoi neighborhood of half-width $\pm 0.125^\circ$ ($~13.9\text{ km}$ north-south).
- **Boundary Buffers:** The domain check explicitly includes the half-cell buffer:  
  `[LAT_MIN - 0.125, LAT_MAX + 0.125]` and `[LON_MIN - 0.125, LON_MAX + 0.125]`  
  Ensuring that boundary node centers receive full symmetric particle capture.
- **Zero Clamping:** Coordinates outside this envelope immediately return `('OUTSIDE_DOMAIN', False, None, None)` without edge clamping.

---

## 2. Test Execution Results Table

| # | Test Description | Coordinates (Lat, Lon) | Expected Grid ID | Measured Grid ID | Inside | Status |
|---|---|---|---|---|---|---|
| 1 | Top-Left Corner (Northwest) | (38.0, 68.0) | `IND_r000_c000` | `IND_r000_c000` | True | **PASS** |
| 2 | Top-Right Corner (Northeast) | (38.0, 98.0) | `IND_r000_c120` | `IND_r000_c120` | True | **PASS** |
| 3 | Bottom-Left Corner (Southwest) | (5.0, 68.0) | `IND_r132_c000` | `IND_r132_c000` | True | **PASS** |
| 4 | Bottom-Right Corner (Southeast) | (5.0, 98.0) | `IND_r132_c120` | `IND_r132_c120` | True | **PASS** |
| 5 | Northern Boundary Just Inside | (38.1249, 75.0) | `IND_r000_c028` | `IND_r000_c028` | True | **PASS** |
| 6 | Northern Boundary Just Outside | (38.1251, 75.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 7 | Northern Far Outside | (40.0, 75.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 8 | Southern Boundary Just Inside | (4.8751, 75.0) | `IND_r132_c028` | `IND_r132_c028` | True | **PASS** |
| 9 | Southern Boundary Just Outside | (4.8749, 75.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 10 | Southern Far Outside | (3.0, 75.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 11 | Western Boundary Just Inside | (20.0, 67.8751) | `IND_r072_c000` | `IND_r072_c000` | True | **PASS** |
| 12 | Western Boundary Just Outside | (20.0, 67.8749) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 13 | Western Far Outside | (20.0, 60.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 14 | Eastern Boundary Just Inside | (20.0, 98.1249) | `IND_r072_c120` | `IND_r072_c120` | True | **PASS** |
| 15 | Eastern Boundary Just Outside | (20.0, 98.1251) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 16 | Eastern Far Outside | (20.0, 102.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 17 | ERA5 Northern Edge Node | (35.0, 75.0) | `IND_r012_c028` | `IND_r012_c028` | True | **PASS** |
| 18 | ERA5 Southern Edge Node | (6.0, 75.0) | `IND_r128_c028` | `IND_r128_c028` | True | **PASS** |
| 19 | ERA5 Western Edge Node | (20.0, 68.0) | `IND_r072_c000` | `IND_r072_c000` | True | **PASS** |
| 20 | ERA5 Eastern Edge Node | (20.0, 97.0) | `IND_r072_c116` | `IND_r072_c116` | True | **PASS** |
| 21 | Center Node (Bhopal region) | (23.25, 77.5) | `IND_r059_c038` | `IND_r059_c038` | True | **PASS** |
| 22 | Near Node (slightly displaced +0.05) | (23.3, 77.55) | `IND_r059_c038` | `IND_r059_c038` | True | **PASS** |
| 23 | Cell Crossing (moves past midpoint 77.63) | (23.3, 77.65) | `IND_r059_c039` | `IND_r059_c039` | True | **PASS** |
| 24 | Exact Midpoint (Banker's rounding) | (23.125, 77.625) | `IND_r060_c038` | `IND_r060_c038` | True | **PASS** |
| 25 | Negative Latitude | (-12.0, 78.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 26 | Negative Longitude | (20.0, -75.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 27 | Equatorial Pacific | (0.0, 160.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |
| 28 | North Pole | (90.0, 0.0) | `OUTSIDE_DOMAIN` | `OUTSIDE_DOMAIN` | False | **PASS** |

---

## 3. Conclusions on Numerical Stability

1. **Coordinate Orientation:** Latitude indexing is strictly descending (Row 0 = 38°N, Row 132 = 5°N), matching standard 2D image matrices and ERA5 NetCDF layout.
2. **No Array Out-of-Bounds:** Bounds are checked prior to indexing, eliminating any possibility of index crashes or negative indexing wraparounds.
3. **Cell Crossings:** Particles cleanly transition from one node to adjacent nodes as displacement exceeds $0.125^\circ$.
