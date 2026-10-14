"""
PHASE 15 — TASK 2: ACQUIRE MISSING 2019 ERA5 DATA
=================================================
Downloads the complete 2019 ERA5 reanalysis surface wind dataset (u10, v10)
from ECMWF Copernicus Climate Data Store (CDS) via cdsapi.

Parameters:
- Product: reanalysis-era5-single-levels
- Variables: 10m_u_component_of_wind, 10m_v_component_of_wind
- Year: 2019
- Months: 01 to 12
- Days: 01 to 31
- Times: 00:00, 06:00, 12:00, 18:00 UTC (4 steps/day = 1,460 steps)
- Bounding Box: [35, 68, 6, 97] (North, West, South, East)
- Format: netcdf

Target File:
- data/raw/era5/2019/era5_2019_instant.nc
"""

import os
import sys
import time
import cdsapi

def acquire_era5_2019(target_dir="data/raw/era5/2019"):
    os.makedirs(target_dir, exist_ok=True)
    target_nc = os.path.join(target_dir, "era5_2019_instant.nc")

    if os.path.exists(target_nc) and os.path.getsize(target_nc) > 50_000_000:
        print(f"[Task 2] File {target_nc} already exists ({os.path.getsize(target_nc)} bytes). Skipping download.")
        return target_nc

    temp_nc = target_nc + ".part"
    print(f"[Task 2] Initializing CDS API client for 2019 ERA5 acquisition...")
    c = cdsapi.Client()

    request_params = {
        'product_type': 'reanalysis',
        'variable': [
            '10m_u_component_of_wind',
            '10m_v_component_of_wind'
        ],
        'year': '2019',
        'month': [f"{i:02d}" for i in range(1, 13)],
        'day': [f"{i:02d}" for i in range(1, 32)],
        'time': ['00:00', '06:00', '12:00', '18:00'],
        'area': [35, 68, 6, 97],
        'format': 'netcdf'
    }

    print("[Task 2] Submitting request to Copernicus Climate Data Store (CDS)...")
    t0 = time.time()
    try:
        c.retrieve(
            'reanalysis-era5-single-levels',
            request_params,
            temp_nc
        )
        t_elapsed = time.time() - t0
        print(f"[Task 2] CDS retrieval completed in {t_elapsed:.1f} seconds.")
        if os.path.exists(temp_nc) and os.path.getsize(temp_nc) > 10_000_000:
            if os.path.exists(target_nc):
                os.remove(target_nc)
            os.rename(temp_nc, target_nc)
            print(f"[Task 2] Successfully saved 2019 ERA5 dataset: {target_nc} ({os.path.getsize(target_nc)} bytes)")
            return target_nc
        else:
            raise RuntimeError(f"Downloaded file {temp_nc} is missing or incomplete (< 10 MB).")
    except Exception as e:
        print(f"[Task 2 ERROR] Failed to download 2019 ERA5 data: {type(e).__name__}: {e}")
        if os.path.exists(temp_nc):
            try:
                os.remove(temp_nc)
            except Exception:
                pass
        raise

if __name__ == "__main__":
    acquire_era5_2019()
