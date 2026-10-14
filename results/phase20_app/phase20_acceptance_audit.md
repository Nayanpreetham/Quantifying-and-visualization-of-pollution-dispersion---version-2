# Phase 20 Final End-to-End Acceptance Audit Report

**Project:** 2D Grid-to-Grid Pollution Dispersion Model for India (50 km National Grid)  
**Audit Phase:** Phase 20 Final Acceptance Audit  
**Audit Date:** 2026-10-15  
**Final Verdict:** **PASS WITH DOCUMENTED LIMITATIONS**  
**Authorization:** **PHASE 21 AUTHORIZED TO BEGIN**  

---

## 1. Application Inspection and Startup Verification

### 1.1 Codebase Inspection
The production codebase was independently inspected across all Phase 20 components:
- Application Entry Point: [`app.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/app.py) (430 lines)
- Application Controller: [`src/phase20/app_controller.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/src/phase20/app_controller.py) (246 lines)
- Observation Provider: [`src/phase20/observation_provider.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/src/phase20/observation_provider.py) (265 lines)
- Map Visualizer: [`src/phase20/map_visualizer.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/src/phase20/map_visualizer.py) (218 lines)
- Automated Test Suite: [`tests/test_phase20_app.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/tests/test_phase20_app.py) (340 lines)
- Acceptance Test Script: [`scripts/run_phase20_acceptance_audit.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/scripts/run_phase20_acceptance_audit.py) (185 lines)

### 1.2 Live Application Startup Test
The Streamlit application was launched using the documented launch command:

```powershell
.\.venv\Scripts\streamlit run app.py --server.headless true --server.port 8501
```

**Startup Log Verification:**
```
Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.
2026-10-15 04:02:40.761 Uvicorn server started on :::8501
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://172.20.45.128:8501
```

**Network and HTTP Endpoint Verification:**
1. **Health Endpoint:** `http://localhost:8501/_stcore/health` returned HTTP status `200` with response body `ok`.
2. **Main Application Page:** `http://localhost:8501/` returned HTTP status `200` with `11,141 bytes` of HTML payload containing the complete Streamlit bundle and application metadata.
3. **Honest Reporting on UI Checks:** Headless browser automation (Playwright/Selenium) is not installed in the local virtual environment. The live server startup, network socket binding on port 8501, HTTP 200 health response, static asset serving, and Folium HTML rendering (75,267 characters) were verified empirically. Visual rendering and full computational pipelines were verified via simulated user workflows.

---

## 2. Verification of Original End-User Workflow

A complete historical dispersion query was evaluated using the primary baseline scenario:
- **Query Date:** `2021-10-15` (National post-monsoon pilot date)
- **User Coordinates:** Latitude $28.6139^\circ\text{N}$, Longitude $77.2090^\circ\text{E}$ (Central Delhi)
- **Transport Horizon:** $24.0\text{ hours}$

### 2.1 Verification Steps and Outcomes

| Step # | Verification Item | Expected Behavior | Actual Empirical Result | Status |
| :---: | :--- | :--- | :--- | :---: |
| **1** | **Source Grid Resolution** | Map $28.6139^\circ\text{N}, 77.2090^\circ\text{E}$ to nearest cell | Resolved to `IND_50KM_r046_c018` (offset: $21.97\text{ km}$ from centroid) | **PASS** |
| **2** | **Synoptic Time Slices** | 4 actual daily ERA5 synoptic releases | Used `00:00, 06:00, 12:00, 18:00 UTC` from `era5_2021_instant.nc` | **PASS** |
| **3** | **Direct Engine Parity** | Identical results to Phase 19 engine | Destination order and fractions match exactly ($\Delta \text{frac} = 0.00\times 10^{-6}$) | **PASS** |
| **4** | **Map & Results Rendering**| Folium interactive map & destination table | 13 destination cells reached; Closure = $1.000000$; Map HTML = 75,267 chars | **PASS** |
| **5** | **Monitoring Status** | Identify ground CAAQMS coverage | Monitored cell (`HISTORICAL_BASELINE_ONLY`, baseline mean: $69.82\ \mu\text{g/m}^3$) | **PASS** |
| **6** | **CSV Export Match** | Downloadable RFC 4180 CSV export | 13 rows exported with full 15-column schema and closure = $1.000000$ | **PASS** |
| **7** | **Measured Runtime** | Real execution runtime reported | First run (cold): $3.914\text{ s}$; Repeated run (cached): $0.127\text{ s}$ | **PASS** |

### 2.2 Sensitivity, Boundary, and Edge-Case Tests

| Test Case | Scenario / Parameters | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Distinct Location 1** | Mumbai ($19.0760^\circ\text{N}, 72.8777^\circ\text{E}$) | Resolves coastal cell `IND_50KM_r025_c009` | Resolved `IND_50KM_r025_c009` (offset: $24.84\text{ km}$) | **PASS** |
| **Distinct Location 2** | Kanpur ($26.4499^\circ\text{N}, 80.3319^\circ\text{E}$) | Resolves IGP cell `IND_50KM_r041_c024` | Resolved `IND_50KM_r041_c024` (offset: $20.45\text{ km}$) | **PASS** |
| **Marine Water Partition**| Mumbai 24h dispersion | Advects into `INTERNAL_UNMODELED_WATER` | 19 of 40 trajectories ($47.5\%$) advected into marine water | **PASS** |
| **Unmonitored Source** | Central India (`IND_50KM_r020_c020`) | Influence index reported strictly as `NaN` | All influence indices = `NaN`, status = `UNMONITORED_SOURCE` | **PASS** |
| **Invalid Date** | Date `2027-01-01` | Rejected at validation layer | Status: `VALIDATION_ERROR`, explanatory message returned | **PASS** |
| **Unsupported Coverage** | Northern Ladakh ($35.60^\circ\text{N}, 76.80^\circ\text{E}$) | Out-of-bounds rejection | Status: `ERROR_UNSUPPORTED_MET_COVERAGE`, extrapolation prevented | **PASS** |

---

## 3. Critical Audit: Observed AQI Ranking and Grid IDs

### 3.1 Problem Identified During Audit
During the audit inspection of `src/phase20/observation_provider.py`, it was noted that the initial implementation of `get_cpcb_aqi_ranking` did not assign a `grid_id_50km` column to CPCB city-level bulletins. Furthermore, duplicate records across dates and missing AQI entries required explicit handling.

### 3.2 Corrective Implementation
The `ObservationProvider` was enhanced to enforce a strict, defensible spatial assignment protocol:

1. **Station-to-Grid Linking:** Cross-referenced CPCB city names with the 103 regulatory stations in `results/phase18_grid_audit/station_to_50km_grid_mapping.csv`.
2. **Defensible 3-Tier Spatial Mapping:**
   - **`SINGLE_50KM_CELL`:** Where all continuous monitoring stations in a city fall strictly within a single 50 km cell, the exact `grid_id_50km` is assigned. (e.g., Agra $\to$ `IND_50KM_r042_c020`, Bengaluru $\to$ `IND_50KM_r011_c018`, Chandigarh $\to$ `IND_50KM_r050_c017`, Kanpur $\to$ `IND_50KM_r041_c024`).
   - **`MULTI_50KM_CELL_URBAN_AREA`:** Where a metropolitan area covers multiple 50 km cells, the grid ID is reported as `MULTIPLE_CELLS (cell_1, cell_2, ...)` without inventing an artificial single-cell assignment. (e.g., Delhi $\to$ `MULTIPLE_CELLS (IND_50KM_r045_c018, IND_50KM_r046_c018)`, Chennai $\to$ `MULTIPLE_CELLS (IND_50KM_r011_c024, IND_50KM_r012_c024)`).
   - **`CITY_LEVEL_REGULATORY_BULLETIN`:** Municipal bulletins from towns lacking CAAQMS stations in the 50 km grid mapping are reported as `UNMAPPED`.
3. **Deduplication and Validation:** Explicitly filtered missing AQI values and deduplicated multiple city reports on the same calendar date.

### 3.3 Audit Verification on Test Date (2021-10-15)
Across the 132 reporting cities in CPCB bulletins on `2021-10-15`:
- **Single-cell mapped cities:** 22 cities assigned exact `grid_id_50km`.
- **Multi-cell urban areas:** 8 cities assigned `MULTIPLE_CELLS`.
- **Unmapped municipal bulletins:** 102 cities assigned `UNMAPPED`.
- **Sorting:** Strictly verified monotonic non-increasing by AQI index value (Top: Bhiwadi = 276, Ballabgarh = 260, Moradabad = 260).
- **Zero Fabrication:** Zero PM2.5-to-AQI synthetic conversions; zero six-year pooled substitutions.

---

## 4. Daily Transport Aggregation Audit

### 4.1 Mathematical Formulation
The daily transport fraction from source cell $i$ to destination cell $j$ on query date $D$ is defined as the arithmetic mean of the ensemble transport fractions across the four daily synoptic release cycles:

$$T_{ij}(D) = \frac{1}{4} \sum_{r=1}^4 T_{ij}^{(r)}$$

where for release $r \in \{00\text{Z}, 06\text{Z}, 12\text{Z}, 18\text{Z}\}$, the transport fraction is:

$$T_{ij}^{(r)} = \frac{c_{j,r}}{N_{\text{ens}}} \quad (N_{\text{ens}} = 10)$$

Substituting into the daily aggregation yields:

$$T_{ij}(D) = \frac{1}{4} \sum_{r=1}^4 \frac{c_{j,r}}{10} = \frac{\sum_{r=1}^4 c_{j,r}}{40}$$

### 4.2 Probability Closure Verification
Summing across all destination pathways (including non-terrestrial categories):

$$\sum_{j \in \text{All Categories}} T_{ij}(D) = \frac{1}{40} \sum_{j} \sum_{r=1}^4 c_{j,r} = \frac{40}{40} = 1.000000$$

**Verification Finding:** Probability closure is mathematically exact. Closure is **not** achieved by normalizing away missing particles. Trajectories exiting into marine waters (`INTERNAL_UNMODELED_WATER`), international domain exits (`DOMAIN_EXIT_EXTERNAL`), or unsupported bounds (`UNSUPPORTED_MET_COVERAGE`) are explicitly accounted for as distinct categories in the denominator.

---

## 5. Map and Output Interpretation Audit

1. **Source Cell Distinction:** The source cell is rendered in bold purple (`#8E44AD`) with a $3\text{px}$ stroke and $45\%$ fill opacity, clearly separated from destination cells. A blue pin indicates the user's clicked coordinates, while a purple circle marker marks the geodetic centroid.
2. **Destination Plume Shading:** Destination polygons are shaded using a sequential color ramp (light peach `#FEE5D9` to deep crimson `#A50F15`) proportional to $T_{ij}$.
3. **Legend and Metric Definition:** The legend explicitly defines the metric as "Modeled Transport Fraction" with a persistent disclaimer: *"Strictly 2D physical transport probability. Does NOT represent destination ambient air quality or AQI."*
4. **Source Influence Index Safeguard:** The metric `source_weighted_transport_influence_index` ($I_{ij} = C_i \times T_{ij}$) is expressed in $\mu\text{g/m}^3\text{-equivalent}$. It is never labeled as destination ambient concentration or AQI.
5. **Unmonitored Sources:** For unmonitored cells, the transport fraction is computed physically, but the influence index is strictly reported as `NaN`. Zero synthetic concentrations are painted on the map or written to CSV.

---

## 6. Acceptance Test Suite Outcomes

All 15 acceptance checks executed via [`scripts/run_phase20_acceptance_audit.py`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/scripts/run_phase20_acceptance_audit.py):

| Check # | Acceptance Check Name | Status | Empirical Outcome |
| :---: | :--- | :---: | :--- |
| **01** | Source Grid Resolution (Delhi) | **PASS** | Resolved `IND_50KM_r046_c018` (offset: $21.97\text{ km}$) |
| **02** | Synoptic Time Handling | **PASS** | Evaluated 4 releases: `00:00, 06:00, 12:00, 18:00 UTC` |
| **03** | Direct Phase 19 Engine Comparison | **PASS** | Exact match with engine output ($\Delta \text{frac} = 0.00\times 10^{-6}$) |
| **04** | Map & Quantitative Results | **PASS** | Folium HTML: 75,267 chars; 13 cells reached; Closure: $1.000000$ |
| **05** | Source Monitoring Availability | **PASS** | Status: `HISTORICAL_BASELINE_ONLY` (Mean: $69.82\ \mu\text{g/m}^3$) |
| **06** | Query CSV Export | **PASS** | Exported and verified 13 rows with full 15-column schema |
| **07** | Real Measured Execution Time | **PASS** | Execution runtime: $3.933\text{ s}$ (within target $< 5\text{ s}$) |
| **08** | Distinct Source Locations | **PASS** | Mumbai $\to$ `IND_50KM_r025_c009`, Kanpur $\to$ `IND_50KM_r041_c024` |
| **09** | Marine Water Boundary Separation | **PASS** | Coastal Mumbai dispersion into `INTERNAL_UNMODELED_WATER`: $47.5\%$ |
| **10** | Unmonitored Source Cell Handling | **PASS** | Influence indices = `NaN`, status = `UNMONITORED_SOURCE_NO_INFLUENCE` |
| **11** | Invalid Date Rejection (2027) | **PASS** | Status: `VALIDATION_ERROR`, date out of bounds rejected |
| **12** | Unsupported Met Coverage (Ladakh >35N) | **PASS** | Status: `ERROR_UNSUPPORTED_MET_COVERAGE`, extrapolation prevented |
| **13** | CPCB AQI Ranking & Grid IDs | **PASS** | 132 cities ranked; Agra $\to$ single, Delhi $\to$ multi, Bhiwadi $\to$ unmapped |
| **14** | OpenAQ PM2.5 Measured Ranking | **PASS** | 9 stations on date; Sorted descending in $\mu\text{g/m}^3$ |
| **15** | Daily Transport Aggregation Consistency | **PASS** | Total particles: 40, Sum of counts: 40, Closure: $1.000000$ |

**Summary:** **15 / 15 CHECKS PASSED (0 FAILURES)**  
Archived log: [`results/phase20_app/phase20_acceptance_tests.csv`](file:///c:/Users/Nayan%20preetham/OneDrive/Documents/UG%20project/Aqi%20prediction%20project/results/phase20_app/phase20_acceptance_tests.csv).

---

## 7. Documented Limitations

The following scientific and structural limitations remain documented and non-blocking:
1. **2D Surface Kinematics:** Trajectories follow 10-meter horizontal winds ($U10, V10$). Vertical shear, thermal inversions, and boundary-layer venting are unmodeled.
2. **Conservative Passive Tracer:** No atmospheric chemistry (secondary sulfate/nitrate formation) or wet/dry deposition is included.
3. **50 km Grid Spatial Resolution:** Hyper-local street-level gradients within a $50\text{ km} \times 50\text{ km}$ ($2,500\text{ km}^2$) box cannot be resolved.
4. **Meteorological Domain Bounds:** 9 peripheral border cells in northern Ladakh ($>35^\circ\text{N}$) and eastern Arunachal Pradesh ($>97^\circ\text{E}$) lack ERA5 reanalysis coverage and return `UNSUPPORTED_MET_COVERAGE`.
5. **Ground Monitoring Network Sparsity:** Only 51 cells have continuous monitors; the remaining 1,329 cells are physically simulated but report `NaN` for source influence.

---

## 8. Final Decision and Milestone Gate

- **Final Verdict:** **`PASS WITH DOCUMENTED LIMITATIONS`**
- **Phase 20 Status:** **ACCEPTED AND COMPLETE**
- **Phase 21 Authorization:** **PHASE 21 (SYNTHESIS, THESIS DOCUMENTATION, AND FINAL PROJECT DEFENSE) IS AUTHORIZED TO BEGIN.**
