# Phase 13 — Task 1: Historical Data Coverage Inventory Report

## 1. Executive Summary

An exhaustive inventory was conducted across all raw ground in-situ observations and ERA5 reanalysis NetCDF files on disk. The key findings are:
1. **Complete 5-Year ERA5 Meteorological Record (2020–2024)**:
   - Exactly **5 continuous calendar years** (60 calendar months, Jan 1, 2020 through Dec 31, 2024) are present on disk with 100% valid coverage.
   - Total synoptic 6-hourly steps: **7,308 steps** ($1,464 + 1,460 + 1,460 + 1,460 + 1,464$).
   - All files contain surface horizontal wind components `u10` and `v10` at 0.25° resolution across the national domain ($[6.0^\circ, 35.0^\circ]\text{N}$, $[68.0^\circ, 97.0^\circ]\text{E}$).
2. **OpenAQ Ground Observations Coverage**:
   - Ground PM2.5 observations exist in `data/real/openaq/pm25_observations.csv` for **2020** (20,760 obs), **2021** (11,592 obs), and **2022** (2,789 obs).
   - For 2023 and 2024, ground observations are missing in this file (sensor uptime gap).
3. **Identification of Missing 6th Year (2019)**:
   - OpenAQ observations exist for 2019 (25,993 obs), but ERA5 NetCDF surface wind files for 2019 are missing from the repository.
   - To expand from the verified 5-year record to a full 6-year record, downloading `era5_2019_instant.nc` (~232 MB from ECMWF CDS) would be required.

## 2. Annual Data Availability Inventory Table

| Year | ERA5 Status | Steps | ERA5 Wind Vars | Size (MB) | OpenAQ PM2.5 Obs | Active Stations | Primary Stations | Coverage Classification |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **2018** | NO | 0 | `None` | 0.0 | 32,342 | 34 | 0 | **OBSERVATIONS_ONLY_ERA5_MISSING** |
| **2019** | NO | 0 | `None` | 0.0 | 25,993 | 19 | 0 | **OBSERVATIONS_ONLY_ERA5_MISSING** |
| **2020** | YES | 1464 | `u10; v10; t2m; sp; blh` | 233.9 | 20,760 | 19 | 1 | **FULL_COUPLED_READY** |
| **2021** | YES | 1460 | `u10; v10; t2m; sp; blh` | 232.9 | 11,592 | 14 | 10 | **FULL_COUPLED_READY** |
| **2022** | YES | 1460 | `u10; v10; t2m; sp; blh` | 232.9 | 2,789 | 5 | 0 | **FULL_COUPLED_READY** |
| **2023** | YES | 1460 | `u10; v10; t2m; sp; blh` | 232.5 | 0 | 0 | 0 | **METEOROLOGY_ONLY_READY** |
| **2024** | YES | 1464 | `u10; v10; t2m; sp; blh` | 233.6 | 0 | 0 | 0 | **METEOROLOGY_ONLY_READY** |
| **2025** | NO | 0 | `None` | 0.0 | 17,575 | 12 | 0 | **OBSERVATIONS_ONLY_ERA5_MISSING** |

## 3. ERA5 Coordinate Compatibility with National Grid

- **National 0.25° Grid Bounds**: Latitude $[5.0^\circ, 38.0^\circ]\text{N}$, Longitude $[68.0^\circ, 98.0^\circ]\text{E}$ (16,093 cells).
- **ERA5 Surface Wind Domain**: Latitude $[6.0^\circ, 35.0^\circ]\text{N}$, Longitude $[68.0^\circ, 97.0^\circ]\text{E}$ (0.25° resolution).
- **Station Coordinate Overlap**: All 10 national monitoring nodes (Agra, Ahmedabad, Chandigarh, Guwahati, Kanpur, Prayagraj, Varanasi) have coordinates located comfortably within the interior of the ERA5 domain (Latitudes: $22.9^\circ\text{N}$ to $30.7^\circ\text{N}$, Longitudes: $72.5^\circ\text{E}$ to $91.8^\circ\text{E}$).
- **Boundary Tracking**: As verified in Phase 8–12, particles that advect beyond the ERA5 or national boundaries are explicitly tracked as `OUTSIDE_DOMAIN` exits without artificial perimeter clamping.

## 4. Minimum Additional Data Required for Full 6 Years

To extend this 5-year continuous pipeline (2020–2024, 60 months) into a 6-year pipeline (2019–2024, 72 months):
- **Missing Dataset**: ERA5 2019 instantaneous surface analysis (`era5_2019_instant.nc`).
- **Parameters Needed**: `u10`, `v10` on 0.25° grid covering India ($6^\circ\text{--}35^\circ\text{N}$, $68^\circ\text{--}97^\circ\text{E}$) at 6-hourly intervals (1,460 steps).
- **Estimated Download Size**: ~230 MB.
- **Current Execution Decision**: Rather than downloading external files, the pipeline will execute the **5 complete, verified continuous years (2020–2024, 60 months)** present on disk, and transparently document the 2019 data gap.