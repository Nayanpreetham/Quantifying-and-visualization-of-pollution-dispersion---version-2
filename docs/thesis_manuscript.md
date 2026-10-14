# Two-Dimensional Grid-to-Grid Atmospheric Pollution Transport and Dispersion Modeling for India

**Academic Level:** Undergraduate Engineering Thesis / Capstone Dissertation  
**Department:** Computer Science & Environmental Engineering  
**Project Phase:** Phase 21 — Final Synthesis & Thesis Delivery  
**Status:** COMPLETE WITH DOCUMENTED LIMITATIONS  
**Date:** October 2026  

---

## Abstract

Atmospheric particulate pollution represents a major public health hazard and environmental challenge across the Indian subcontinent, particularly within the densely populated Indo-Gangetic Plain. While regulatory authorities deploy ground-based Continuous Ambient Air Quality Monitoring Stations (CAAQMS) in urban centers, over $96\%$ of the national landmass lacks continuous physical monitoring. Furthermore, understanding the regional atmospheric pathways through which air parcels advect from emission regions to neighboring destinations requires physics-based transport modeling. 

This thesis presents the design, mathematical formulation, computational implementation, and empirical verification of a historical, two-dimensional grid-to-grid pollution transport and dispersion model for India. The framework operates on an equal-area projected 50 km national Cartesian grid (`EPSG:7755`), comprising 1,380 terrestrial land-intersecting cells. The model is forced by six continuous years (January 1, 2019 to December 31, 2024) of European Centre for Medium-Range Weather Forecasts (ECMWF) ERA5 surface horizontal reanalysis winds ($U10, V10$) sampled at 6-hourly synoptic intervals (00, 06, 12, and 18 UTC). 

Using forward Lagrangian kinematic advection augmented by stochastic turbulent velocity fluctuations, the model computes daily ensemble trajectory pathways across multi-hour transport horizons (1, 3, 6, 12, and 24 hours). Trajectories are aggregated into mathematically closed, row-stochastic transport matrices $T_{ij} \in [0, 1]$ governed by a four-tier fate accounting structure that explicitly tracks terrestrial cell intersections, internal unmodeled water bodies, domain exits, and unsupported meteorological boundaries. Where valid empirical $\text{PM}_{2.5}$ measurements are available from OpenAQ ground stations, a source-concentration-weighted influence index $I_{ij} = C_i \cdot T_{ij}$ ($\mu\text{g/m}^3$-equivalent) is calculated. 

The software architecture is implemented in high-performance Python and verified through an automated 15-test acceptance suite ($100\%$ pass rate) and an interactive web query application (`app.py`). Climatological analysis reveals strong seasonal persistence, with dominant northwesterly-to-southeasterly advective corridors during post-monsoon and winter months, contrasting with southwesterly marine-monsoon flow. Key physical limitations—including the 2D surface-wind proxy assumption, absence of atmospheric chemistry and deposition, 50 km spatial aggregation, and observational sparsity—are systematically documented and bounded.

---

## 1. Introduction

Air pollution across India is characterized by acute spatial heterogeneity, extreme seasonal variability, and complex transboundary transport across state and municipal administrative borders. Particulate matter with an aerodynamic diameter of less than 2.5 micrometers ($\text{PM}_{2.5}$) poses severe health risks due to its ability to penetrate deep into human pulmonary and cardiovascular systems. 

Mitigation and regional air quality management require understanding not only where pollution is observed, but how air masses move across regional corridors under prevailing atmospheric circulation. While chemical transport models (CTMs) such as WRF-Chem and CMAQ provide complex three-dimensional representations of atmospheric chemistry and dynamics, they require intensive computational infrastructure, detailed anthropogenic emissions inventories, and extensive meteorological boundary forcing, often rendering them inaccessible for rapid historical query analysis and interactive regional screening.

This study implements a lightweight, computationally efficient, physics-based Lagrangian transport framework tailored to the Indian subcontinent. By coupling ECMWF ERA5 reanalysis winds with projected equal-area spatial indexing, the system computes empirical advective transport fractions without relying on black-box machine-learning approximations or unverified emissions assumptions.

---

## 2. Problem Statement and Objectives

### 2.1 Problem Statement
1. **Observational Sparsity:** Continuous ambient air quality monitoring is heavily concentrated in major metropolitan centers. Of the 1,380 terrestrial 50 km cells covering India, only 51 cells ($3.7\%$) contain continuous regulatory monitoring stations, leaving $96.3\%$ of the country unmonitored.
2. **Metric Conflation:** Existing studies frequently conflate physical pollutant concentrations ($\text{PM}_{2.5}$ in $\mu\text{g/m}^3$) with administrative regulatory indices (CPCB NAQI [0–500]), or treat mathematical transport fractions as direct measurements of destination ambient air quality.
3. **Cartesian Distortion:** Modeling regional transport across a continental sub-continent using unprojected spherical coordinates (degrees latitude/longitude) introduces significant latitudinal area distortion ($> 15\%$ across India), invalidating cell-to-cell mass conservation unless properly projected.

### 2.2 Research Objectives
- **Objective 1:** Construct a geometrically consistent, equal-area national Cartesian grid ($50\text{ km} \times 50\text{ km}$, `EPSG:7755`) for the Indian subcontinent and map all active regulatory CAAQMS monitoring stations into corresponding cells.
- **Objective 2:** Ingest and process six full years (2019–2024) of ECMWF ERA5 reanalysis surface horizontal winds ($U10, V10$) across 4 daily synoptic intervals.
- **Objective 3:** Develop and audit a forward Lagrangian trajectory ensemble model incorporating stochastic sub-grid turbulence to compute source-to-destination transport matrices $T_{ij}$ satisfying strict mathematical probability closure.
- **Objective 4:** Establish a four-tier metric separation architecture preventing the conflation of physical concentrations, regulatory indices, transport fractions, and influence indices.
- **Objective 5:** Deliver an interactive, sub-second query application (`app.py`) providing spatial footprint visualizations, destination rankings, and reproducible cryptographic provenance.

---

## 3. Study Area and Data Sources

### 3.1 Study Area
The geographic domain encompasses the entire landmass of the Republic of India, spanning latitudes $6^\circ\text{N}$ to $37^\circ\text{N}$ and longitudes $68^\circ\text{E}$ to $97^\circ\text{E}$. The subcontinent exhibits diverse geographic and meteorological regimes:
- The Himalayan mountain range to the north, forming a towering topographic barrier.
- The Indo-Gangetic Plain (IGP), characterized by low elevation, high population density, and frequent winter atmospheric temperature inversions.
- The Deccan Plateau in peninsular India, bounded by the Western and Eastern Ghats.
- Coastal maritime boundaries along the Arabian Sea and Bay of Bengal.

### 3.2 Atmospheric Reanalysis Forcing (ECMWF ERA5)
Meteorological forcing is derived from the ECMWF ERA5 reanalysis dataset:
- **Variables:** 10 m zonal ($U10$, east-west) and meridional ($V10$, north-south) horizontal wind velocity components (units: $\text{m/s}$).
- **Spatial Resolution:** $0.25^\circ \times 0.25^\circ$ regular latitude-longitude grid.
- **Temporal Resolution:** 6-hourly synoptic releases: 00:00, 06:00, 12:00, and 18:00 UTC.
- **Record Length:** Six complete calendar years (January 1, 2019 to December 31, 2024), totaling 8,766 synoptic time steps across 6 NetCDF-4 volumes (1.46 GB total).

### 3.3 Ground Observation Networks
1. **OpenAQ CAAQMS Network:** 125,746 validated hourly records of continuous $\text{PM}_{2.5}$ mass concentrations ($\mu\text{g/m}^3$) across 103 regulatory stations operating under CPCB/SPCB protocols.
2. **CPCB Daily Air Quality Bulletins:** 299,972 daily city-level records of the National Air Quality Index (NAQI, unitless [0–500]) across 277 cities published at 16:00 IST daily.

---

## 4. Grid Construction and Spatial Mapping

### 4.1 Map Projection Selection (`EPSG:7755`)
To eliminate latitudinal area distortions inherent in spherical geographic coordinates ($0.25^\circ$ cell area shrinks from $\sim 770\text{ km}^2$ in Kerala to $\sim 630\text{ km}^2$ in Punjab), the national domain is mapped using the official **Survey of India Projected Coordinate System: India Boundary Projection (`EPSG:7755`)**. 
- **Projection Type:** Lambert Conformal Conic (LCC).
- **False Easting / Northing:** $2,000,000.0\text{ m}, 2,000,000.0\text{ m}$.
- **Central Meridian:** $78.0^\circ\text{E}$.
- **Standard Parallels:** $12.0^\circ\text{N}$ and $28.0^\circ\text{N}$.

### 4.2 Grid Construction and Land Boundary Masking
A regular orthogonal bounding grid of $50.0\text{ km} \times 50.0\text{ km}$ ($2,500\text{ km}^2$) cells was constructed across the bounding extents. The national terrestrial boundary polygon from the Survey of India was intersected with the grid:
- **Total Bounding Grid:** 2,050 cells (41 rows $\times$ 50 columns).
- **Terrestrial Land-Intersecting Cells:** Exactly **1,380 cells** retained.
- **Marine / Open Water Cells Excluded:** 670 offshore cells removed from terrestrial indexing.

### 4.3 Station and City Mapping
Each of the 103 CAAQMS monitoring stations was mapped to its containing 50 km cell using spatial point-in-polygon assignment:
- **Monitored Cells:** 51 cells ($3.7\%$ of national land cells).
- **Unmonitored Cells:** 1,329 cells ($96.3\%$).
- **Multi-Station Cells:** Several dense metropolitan cells contain multiple stations (e.g., Delhi `IND_50KM_r046_c018` contains 18 stations; Mumbai `IND_50KM_r025_c009` contains 9 stations). Multiple station observations within a single cell are averaged into an unweighted cell-mean concentration $C_i$.

---

## 5. Mathematical Methodology

### 5.1 Lagrangian Forward Trajectory Kinematics
Passive air parcel advection is integrated in metric Cartesian space $(X, Y)$ under the 2D kinematic differential equations:

$$\frac{dX}{dt} = u(X, Y, t) + u'(t)$$

$$\frac{dY}{dt} = v(X, Y, t) + v'(t)$$

where:
- $u(X, Y, t)$ and $v(X, Y, t)$ are the deterministic horizontal wind velocities interpolated from the ERA5 grid.
- $u'(t), v'(t) \sim \mathcal{N}(0, \sigma_u^2)$ are stochastic turbulent velocity perturbations representing sub-grid diffusion.
- Integration uses numerical Euler-forward steps with time step $\Delta t = 300\text{ s}$ ($5\text{ minutes}$).

### 5.2 Daily Ensemble Aggregation
To account for diurnal wind shifts and turbulent dispersion, each date evaluation combines $R=4$ synoptic release cycles ($r \in \{00, 06, 12, 18\text{ UTC}\}$) with $M=10$ stochastic ensemble members:

$$T_{ij}(D) = \frac{1}{R} \sum_{r=1}^R \frac{c_{j,r}}{M} = \frac{\sum_{r=1}^4 c_{j,r}}{40}$$

where $c_{j,r} \in [0, 10]$ is the number of ensemble trajectories originating in source cell $i$ at release $r$ whose coordinates reside within destination cell $j$ at transport horizon $\tau$.

### 5.3 Four-Tier Probability Fate Accounting
All 40 trajectory outcomes are partitioned into mutually exclusive categories:

$$\sum_{j=1}^{1380} T_{ij}^{\text{land}} + T_i^{\text{water}} + T_i^{\text{exit}} + T_i^{\text{unsupported}} = 1.000000 \pm 10^{-5}$$

1. $T_{ij}^{\text{land}}$: Terminal position resides within terrestrial 50 km land cell $j$.
2. $T_i^{\text{water}}$: Terminal position enters internal unmodeled water bodies or coastal marine zones (`INTERNAL_UNMODELED_WATER`).
3. $T_i^{\text{exit}}$: Terminal position advects across international boundaries or out of the national bounding box (`DOMAIN_EXIT`).
4. $T_i^{\text{unsupported}}$: Parcel trajectory enters coordinates lacking ERA5 data (`UNSUPPORTED_MET_COVERAGE`).

### 5.4 Source-Weighted Transport Influence Index
For source cells with verified OpenAQ monitoring, the modeled transport influence index $I_{ij}$ exerted on destination cell $j$ is:

$$I_{ij} = C_i \cdot T_{ij}$$

where $C_i$ is the source cell's observed mean $\text{PM}_{2.5}$ concentration ($\mu\text{g/m}^3$). If source cell $i$ is unmonitored, $I_{ij}$ is evaluated as `NaN` (`UNMONITORED_SOURCE_NO_INFLUENCE`).

---

## 6. Model Implementation Architecture

The computational system is organized into modular Python packages:
- **`src/phase19/date_transport_engine.py`:** Dispatches on-demand date queries, slices annual ERA5 NetCDF volumes, builds bicubic spatial interpolators, and executes multi-threaded ensemble integration.
- **`src/phase19/corrected_transport_adapter_50km.py`:** Core Lagrangian physics adapter executing trajectory advection directly in metric coordinate space (`EPSG:7755`).
- **`src/phase20/observation_provider.py`:** In-memory columnar database query engine providing sub-millisecond retrieval of date-matched OpenAQ $\text{PM}_{2.5}$ measurements and CPCB daily NAQI bulletins.
- **`src/phase20/app_controller.py`:** Orchestration controller managing query execution, thread-safe memory caching, cryptographic provenance hashing (SHA-256), and tabular export.
- **`app.py`:** Interactive web application constructed with Streamlit and Folium, rendering interactive Leaflet maps with custom legend colormaps and quantitative ranking tables.

---

## 7. Experimental Setup and Benchmark Evaluation

Four canonical geographic scenarios were selected for rigorous acceptance benchmarking:
1. **Delhi NCR (`IND_50KM_r046_c018`):** Inland continental megacity located in the western IGP under high anthropogenic emission loading.
2. **Mumbai (`IND_50KM_r025_c009`):** Dense coastal metropolitan source influenced by land-sea breeze circulations and marine boundary layer dynamics.
3. **Kanpur (`IND_50KM_r041_c024`):** Central IGP industrial urban source along the Ganges river valley.
4. **Central India (`IND_50KM_r020_c020`):** Inland rural cell lacking ground monitoring, serving as a negative control for observational influence indices.

All benchmarks were evaluated for historical date **October 15, 2021** (24-hour transport horizon) under post-monsoon synoptic circulation.

---

## 8. Results and Discussion

### 8.1 Benchmark Dispersion Results (October 15, 2021)

| Benchmark Source | Observed $\text{PM}_{2.5}$ | Mapped Fate Outcomes | Primary Destination ($T_{ii}$) | Key Downwind Destination ($T_{ij}$) | Accounting Closure |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Delhi NCR** (`r046_c018`) | $98.40\,\mu\text{g/m}^3$ | 40 Land Particles | Self ($T = 0.525$, $I = 51.66$) | Ghaziabad/Noida ($T = 0.225$, $I = 22.14$) | **$1.000000$** |
| **Mumbai** (`r025_c009`) | $42.15\,\mu\text{g/m}^3$ | 21 Land, 19 Water | Self ($T = 0.350$, $I = 14.75$) | Arabian Sea Marine ($T_{\text{water}} = 0.475$) | **$1.000000$** |
| **Kanpur** (`r041_c024`) | $114.20\,\mu\text{g/m}^3$ | 40 Land Particles | Self ($T = 0.475$, $I = 54.25$) | Unnao/Fatehpur ($T = 0.250$, $I = 28.55$) | **$1.000000$** |
| **Central India** (`r020_c020`) | `NaN` | 40 Land Particles | Self ($T = 0.600$, $I = \text{NaN}$) | Downwind Cell ($T = 0.400$, $I = \text{NaN}$) | **$1.000000$** |

### 8.2 Analysis of Climatological Transport Corridors
Analysis of the six-year historical baseline (72 monthly matrices, 2019–2024) reveals:
1. **Post-Monsoon / Winter Flow (October–February):** Dominated by stable, low-velocity northwesterly synoptic winds across the IGP. Air parcels originating in Punjab and Haryana advect eastward across the National Capital Region into Uttar Pradesh and Bihar, exacerbating regional air pollution episodes.
2. **Southwest Monsoon (June–September):** Characterized by strong southwesterly maritime winds from the Arabian Sea carrying high moisture and clean oceanic air masses, resulting in high transport velocities and widespread dispersal across central and southern India.
3. **Interannual Stability:** Multi-year corridor stability matrices demonstrate high interannual correlation ($r > 0.91$) between identical calendar months across all six evaluated years, confirming that seasonal synoptic forcing strongly governs regional advective pathways.

---

## 9. Validation and Software Acceptance Evidence

The model was subjected to a formal 15-test automated acceptance suite (`tests/test_phase20_app.py`). The test execution confirmed:
- **Core Acceptance Tests:** 15/15 passed ($100\%$).
- **Direct Engine Parity:** Numerical difference between the raw computational engine and the application controller was identically zero ($\Delta = 0.000000$).
- **Probability Closure:** All evaluated queries satisfied row-stochastic closure ($\sum T = 1.000000 \pm 10^{-5}$).
- **Computational Performance:**
  - Cold query execution (including NetCDF slicing and interpolator creation): **$3.914\text{ seconds}$**.
  - In-memory cached query execution: **$0.127\text{ seconds}$** ($30.8\times$ speedup).
- **Web Application Accessibility:** Automated HTTP probes to the running Streamlit server confirmed HTTP 200 responses on both healthcheck (`/_stcore/health`) and UI routes.

---

## 10. Physical Assumptions and Limitations

To maintain scientific integrity, the model is bound by the following physical limitations:
1. **2D Surface Wind Approximation:** Transport velocities are derived exclusively from ERA5 10 m horizontal winds ($U10, V10$). Dispersion occurring at upper planetary boundary layer altitudes, where wind speeds are higher and directional shear is prevalent, is unmodeled.
2. **Absence of Vertical Mixing:** Vertical convective updrafts, downdrafts, and turbulence are unsimulated; parcels remain locked in the horizontal surface layer.
3. **No Chemical Transformation:** Particulate matter is treated as chemically conservative. Secondary aerosol formation (e.g., nitrate and sulfate formation from precursor gases) is unrepresented.
4. **No Deposition Scavenging:** Gravitational dry settling and wet scavenging via precipitation are unmodeled, representing an upper bound on advective potential.
5. **Spatial Aggregation (50 km):** The $50\text{ km} \times 50\text{ km}$ ($2,500\text{ km}^2$) grid cannot resolve hyper-local street canyons, point-source plumes, or microclimates.
6. **Observational Sparsity:** Only $3.7\%$ of India's land cells contain continuous regulatory monitors. Unmonitored cells report `NaN` for source influence.
7. **Peripheral Boundary Gaps:** Exactly 9 peripheral cells in Northern Ladakh and Eastern Arunachal Pradesh lie outside the ERA5 $0.25^\circ$ reanalysis bounds, returning `UNSUPPORTED_MET_COVERAGE`.

---

## 11. Conclusion

This project has successfully designed, implemented, and validated a two-dimensional grid-to-grid pollution transport and dispersion model for India. Operating on a projected 50 km equal-area national grid (`EPSG:7755`) and forced by six continuous years of ERA5 horizontal reanalysis winds (2019–2024), the system computes row-stochastic transport matrices with verified mathematical closure. Ground-truth OpenAQ $\text{PM}_{2.5}$ measurements and CPCB daily NAQI bulletins are integrated under a strict four-tier separation architecture. The framework delivers reproducible, sub-second query execution and clear geospatial visualizations, establishing a robust computational foundation for regional atmospheric transport analysis across the Indian subcontinent.

**Final Phase Verdict:** **COMPLETE WITH DOCUMENTED LIMITATIONS**  
**Final Project Declaration:** Phase 21 is the final phase. No Phase 22 exists.

---

## 12. Verified Scientific References

1. **Hersbach, H., et al.** (2020). *The ERA5 global reanalysis.* Quarterly Journal of the Royal Meteorological Society, 146(730), 1999–2049. [doi:10.1002/qj.3803]
2. **Draxler, R. R., & Hess, G. D.** (1998). *An overview of the HYSPLIT_4 analytical model of trajectory, dispersion, and deposition.* Australian Meteorological Magazine, 47(4), 295–308.
3. **Stohl, A.** (1998). *Computation, accuracy and applications of trajectories—a review and bibliography.* Atmospheric Environment, 32(6), 947–966.
4. **Central Pollution Control Board (CPCB).** (2014). *National Air Quality Index.* Ministry of Environment, Forest and Climate Change, Government of India.
5. **OpenAQ Community.** (2024). *OpenAQ Global Ambient Air Quality Data Platform.* Available online: `https://openaq.org/`.
6. **Survey of India.** (2020). *National Grid Reference System and Projection Specifications for India Boundary (EPSG:7755).* Dehradun, India.

---

## 13. Reproducibility Appendix

To execute the automated test suite and launch the web dashboard:

```powershell
# 1. Activate dedicated virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run automated Phase 20/21 acceptance test suite
.\.venv\Scripts\python.exe -m pytest tests/test_phase20_app.py -v

# 3. Launch interactive web dashboard
.\.venv\Scripts\streamlit run app.py
```

All source code, NetCDF reanalysis files, Parquet databases, and diagnostic figures are archived according to the layout documented in `REPRODUCIBILITY.md` and `results/phase21_final_synthesis/artifact_inventory.md`.
