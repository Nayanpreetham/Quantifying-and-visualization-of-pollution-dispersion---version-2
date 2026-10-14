"""
PHASE 15 — TASK 1: INSPECTION OF ERA5 DOWNLOAD & PROCESSING INFRASTRUCTURE
==========================================================================
Inspects existing ERA5 files, coordinate conventions, required variables,
temporal frequency, spatial domain, and CDS credentials (without leaking secrets).
Generates: results/phase15_six_year/era5_download_specification.json
"""

import os
import sys
import json
import xarray as xr
import pandas as pd

def inspect_infrastructure(base_dir=".", out_dir="results/phase15_six_year"):
    os.makedirs(out_dir, exist_ok=True)
    out_spec = os.path.join(out_dir, "era5_download_specification.json")

    # Inspect 2020 file as reference
    ref_file = os.path.join(base_dir, "data/raw/era5/2020/era5_2020_instant.nc")
    ds = xr.open_dataset(ref_file)

    t_coord = "valid_time" if "valid_time" in ds else "time"
    times = pd.to_datetime(ds[t_coord].values)
    lats = ds["latitude"].values
    lons = ds["longitude"].values

    # Check CDS API config existence without printing token
    cdsapirc_path = os.path.expanduser("~/.cdsapirc")
    cdsapirc_exists = os.path.exists(cdsapirc_path)

    spec = {
        "dataset_name": "reanalysis-era5-single-levels",
        "product_type": "reanalysis",
        "target_calendar_year": 2019,
        "is_leap_year": False,
        "expected_synoptic_steps": 1460,  # 365 days * 4 steps/day
        "temporal_frequency": "6-hourly",
        "synoptic_hours_utc": ["00:00", "06:00", "12:00", "18:00"],
        "required_variables": [
            "10m_u_component_of_wind",
            "10m_v_component_of_wind"
        ],
        "nc_variable_names": ["u10", "v10"],
        "u10_units_expected": "m s**-1",
        "v10_units_expected": "m s**-1",
        "spatial_bounding_box": {
            "north": 35.0,
            "west": 68.0,
            "south": 6.0,
            "east": 97.0,
            "area_cds_parameter": [35.0, 68.0, 6.0, 97.0]
        },
        "spatial_grid_step_deg": 0.25,
        "latitudes_count": len(lats),
        "longitudes_count": len(lons),
        "lat_ordering": "DESCENDING" if lats[0] > lats[-1] else "ASCENDING",
        "lon_ordering": "ASCENDING" if lons[0] < lons[-1] else "DESCENDING",
        "target_file_directory": "data/raw/era5/2019",
        "target_instant_file": "data/raw/era5/2019/era5_2019_instant.nc",
        "cdsapirc_found": cdsapirc_exists,
        "pipeline_compatibility": {
            "physics_engine": "2D Lagrangian ensemble (N=20, dt in [1, 3, 6, 12, 24]h)",
            "aggregation": "Unconditional Phase 10 time-aggregation",
            "zero_imputation": False,
            "clamping": False
        }
    }

    ds.close()

    with open(out_spec, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)

    print(f"[Task 1] Specification written to {out_spec}")
    return spec

if __name__ == "__main__":
    inspect_infrastructure()
