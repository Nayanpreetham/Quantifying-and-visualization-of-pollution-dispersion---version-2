# Reproducibility Guide — India National 2D Pollution Dispersion Project

**Project:** Two-Dimensional Grid-to-Grid Pollution Transport and Dispersion Model for India  
**Phase:** Phase 21 — Final Synthesis & Reproducibility Package  
**Target Environment:** Windows 10/11 x64, Linux, or macOS  
**Tested Python Version:** Python 3.12 / 3.13  

---

## 1. System Requirements & Environment Setup

### 1.1 Python Environment
This project runs entirely on standard Python with scientific data libraries. A dedicated virtual environment is strongly recommended:

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 1.2 Core Python Dependencies
The model requires the following packages (all verified functional in `.venv`):

| Package | Purpose |
| :--- | :--- |
| `numpy` | Vectorized numerical operations and matrix manipulations |
| `scipy` | Regular-grid interpolation (`RegularGridInterpolator`) for spatial wind fields |
| `pandas` | Tabular data structures and CSV/Parquet export |
| `pyarrow` | High-performance Parquet storage engine for CPCB and OpenAQ observations |
| `pyproj` | Map projection transformations between `EPSG:4326` and `EPSG:7755` |
| `netCDF4` | Direct multi-dimensional slicing of annual ECMWF ERA5 NetCDF-4 files |
| `folium` | Interactive Leaflet geospatial map generation |
| `branca` | Colormap styling and custom legend generation for Folium |
| `streamlit` | Lightweight web dashboard framework for `app.py` |

To install all required packages:
```bash
pip install numpy scipy pandas pyarrow pyproj netCDF4 folium branca streamlit
```

---

## 2. Authoritative Data Files and Expected Directory Layout

The application and computational engines rely on the following verified file structure:

```
Aqi prediction project/
├── data/
│   ├── raw/
│   │   ├── era5/
│   │   │   ├── 2019/era5_2019_instant.nc   # Annual ERA5 u10, v10 (6-hourly synoptic)
│   │   │   ├── 2020/era5_2020_instant.nc
│   │   │   ├── 2021/era5_2021_instant.nc
│   │   │   ├── 2022/era5_2022_instant.nc
│   │   │   ├── 2023/era5_2023_instant.nc
│   │   │   └── 2024/era5_2024_instant.nc
│   │   ├── cpcb/
│   │   │   └── aqi_data/*.csv              # 277 raw CPCB daily city bulletin files
│   │   └── geography/
│   │       └── india_land_boundary.geojson # Official Survey of India land boundary
│   ├── real/
│   │   └── openaq/
│   │       ├── pm25_observations.csv       # 125,746 validated CAAQMS hourly observations
│   │       └── station_metadata.csv        # Metadata for 103 regulatory stations
│   └── processed/
│       ├── cpcb_bulletins_unified.parquet  # Optimized columnar index (299,972 rows)
│       └── openaq_pm25_observations.parquet# Optimized columnar index (125,746 rows)
├── results/
│   ├── phase18_grid_audit/
│   │   ├── india_50km_grid.csv             # 1,380 terrestrial 50 km cells metadata
│   │   ├── india_50km_grid.geojson         # 1,380 cell boundary polygons in EPSG:7755
│   │   └── station_to_50km_grid_mapping.csv# Station-to-cell assignment table
│   └── phase19_transport/
│       └── matrices/
│           └── monitored_cells_concentration_summary.csv # 51-cell baseline summaries
```

---

## 3. Execution Commands

### 3.1 Launching the Interactive Web Application
To run the interactive Streamlit dashboard:

```powershell
# Windows PowerShell
.\.venv\Scripts\streamlit run app.py

# Linux / macOS
streamlit run app.py
```
The application will launch and bind to `http://localhost:8501`.

### 3.2 Executing the Automated Verification Test Suite
To run the 15-check automated verification suite covering inputs, engine parity, boundary conditions, and reproducibility:

```powershell
.\.venv\Scripts\python.exe tests/test_phase20_app.py
```
Outputs are recorded in: `results/phase20_app/phase20_test_results.csv`.

### 3.3 Executing the Acceptance Audit Runner
To run the independent 15-check acceptance audit script:

```powershell
.\.venv\Scripts\python.exe scripts/run_phase20_acceptance_audit.py
```
Outputs are recorded in: `results/phase20_app/phase20_acceptance_tests.csv`.

---

## 4. How to Reproduce Documented Query Benchmarks

### 4.1 Programmatic Execution (Python API)
Any historical query can be executed programmatically in three lines using `AppController`:

```python
from src.phase20.app_controller import AppController

ctrl = AppController()

# Execute Delhi baseline post-monsoon query
result = ctrl.execute_query(
    year=2021, month=10, day=15,
    lat=28.6139, lon=77.2090,
    horizon_hours=24.0,
    use_cache=True
)

df = result['results_table']
print(f"Status: {result['status']}")
print(f"Resolved Cell: {result['source_info']['grid_id_50km']}")
print(f"Probability Closure Sum: {result['probability_closure_sum']:.6f}")
print("Top 3 Destination Pathways:")
print(df[['rank', 'destination', 'category', 'daily_transport_fraction', 'distance_km', 'source_weighted_transport_influence_index']].head(3))
```

### 4.2 Benchmark Query Catalog
Pre-computed, verified query outputs with sidecar provenance JSON are archived in `results/phase20_app/sample_queries/`:

1. **Central Delhi NCR (`delhi_20211015_24h.csv`):**
   - Inputs: Date `2021-10-15`, Lat `28.6139`, Lon `77.2090`, Horizon `24h`.
   - Resolved Cell: `IND_50KM_r046_c018` (Centroid offset: $21.97\text{ km}$).
   - Destination Pathways: 13 cells reached across Haryana/UP. Top cell: `IND_50KM_r045_c017` ($T_{ij} = 0.2000$).
   - Closure: $1.000000$.
2. **Kanpur IGP Industrial Corridor (`kanpur_20211015_24h.csv`):**
   - Inputs: Date `2021-10-15`, Lat `26.4499`, Lon `80.3319`, Horizon `24h`.
   - Resolved Cell: `IND_50KM_r041_c024` (Centroid offset: $20.45\text{ km}$).
   - Destination Pathways: 14 cells reached downwind. Top cell: `IND_50KM_r041_c025` ($T_{ij} = 0.2250$).
   - Closure: $1.000000$.
3. **Mumbai Coastal Marine Partition (`mumbai_20211015_24h.csv`):**
   - Inputs: Date `2021-10-15`, Lat `19.0760`, Lon `72.8777`, Horizon `24h`.
   - Resolved Cell: `IND_50KM_r025_c009` (Centroid offset: $24.84\text{ km}$).
   - Category Breakdown: Terrestrial Land: $52.5\%$, `INTERNAL_UNMODELED_WATER`: **$47.5\%$** (19/40 particles).
   - Closure: $1.000000$.
4. **Rural Unmonitored Cell (`unmonitored_central_20211015_24h.csv`):**
   - Inputs: Date `2021-10-15`, Grid ID `IND_50KM_r020_c020`, Horizon `24h`.
   - Destination Pathways: 7 cells reached.
   - Influence Index: Strictly **`NaN`** across all rows (`UNMONITORED_SOURCE_NO_INFLUENCE`).
   - Closure: $1.000000$.

---

## 5. Measured Runtime and Cache Performance

*(Measured on local host: Intel i7/AMD Ryzen x64, Python 3.12, Windows 11)*:
- **Cold Simulation Runtime:** $3.6\text{ s} - 3.9\text{ s}$ per query.
  - Slices 4 synoptic releases $\times$ 10 ensemble members $\times$ 24 hourly integration steps.
- **Cached Simulation Runtime:** **$0.12\text{ s} - 0.15\text{ s}$** per query.
  - Managed by in-memory composite cache keyed on `(year, month, day, source_grid_id, horizon_hours)`.
- **CPCB AQI Ranking (277 cities):** $< 0.09\text{ s}$ via columnar Parquet.
- **OpenAQ PM2.5 Ranking (103 stations):** $< 0.05\text{ s}$ via columnar Parquet.
- **Folium Interactive HTML Map Generation:** $< 0.30\text{ s}$ ($75\text{ KB}$ self-contained HTML).

---

## 6. Common Failure Modes and Error Handling

| Scenario | Input Example | Expected Behavior / System Output |
| :--- | :--- | :--- |
| **Out-of-Range Date** | Year 2027 or 2018 | `VALIDATION_ERROR`: Explains supported baseline is 2019-01-01 to 2024-12-31. |
| **Invalid Calendar Date** | `2021-02-30` | `VALIDATION_ERROR`: Calendar parse failure. |
| **Unsupported Horizon** | Horizon `8.0h` | `VALIDATION_ERROR`: Explains supported horizons are `[1.0, 3.0, 6.0, 12.0, 24.0]`. |
| **Coordinates in Ocean** | Lat $15.0^\circ\text{N}$, Lon $65.0^\circ\text{E}$ | `ERROR_LOCATION_IN_WATER` or `ERROR_LOCATION_OUTSIDE_GRID`. |
| **Northern Ladakh Border** | Lat $35.6^\circ\text{N}$, Lon $76.8^\circ\text{E}$ | `ERROR_UNSUPPORTED_MET_COVERAGE`: Halts execution; extrapolation prohibited. |
| **Unmonitored Source Cell** | Central India `r020_c020` | Computes physical transport $T_{ij}$, sets influence index to `NaN` (Unmonitored). |
| **CPCB Town Without CAAQMS** | Bhiwadi, Ballabgarh | Displays CPCB bulletin AQI, labels `grid_id_50km = UNMAPPED`. |

---

## 7. Transport-Category Accounting Interpretation

Every trajectory is assigned to one of four mutually exclusive categories:
1. `VALID_LAND_DESTINATION` (`IND_50KM_rXXX_cYYY`): Valid terrestrial Indian land cell ($f_{\text{land}} > 0$).
2. `INTERNAL_UNMODELED_WATER`: Coastal marine/ocean water within the national grid bounding matrix.
3. `DOMAIN_EXIT_EXTERNAL`: Physical parcel exit beyond the national grid boundary envelope into international borders or international waters.
4. `UNSUPPORTED_MET_COVERAGE`: Parcel position outside the ERA5 reanalysis bounding box $[6^\circ\text{N}–35^\circ\text{N}, 68^\circ\text{E}–97^\circ\text{E}]$.

**Mathematical Rule:** The transport fraction $T_{ij}$ is normalized across all 40 particles:
$$T_{ij} = \frac{c_j}{40}$$
Summing across all 4 categories always equals $1.000000 \pm 10^{-5}$.
Non-terrestrial outcomes are never discarded, filtered, or normalized away.
