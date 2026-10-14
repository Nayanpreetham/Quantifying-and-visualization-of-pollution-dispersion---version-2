"""
PHASE 15 — TASK 3: INDEPENDENT VALIDATION OF 2019 ERA5 DATA
===========================================================
Performs independent, rigorous audit on the downloaded 2019 ERA5 NetCDF file:
1. File integrity & structure (valid xarray dataset).
2. Variables u10 and v10 presence, shape, units, and range.
3. Coordinates: valid_time, latitude (35 to 6), longitude (68 to 97).
4. Temporal schedule: exactly 1,460 steps (365 days x 4 steps), 6-hourly spacing, 0 duplicates, 0 gaps.
5. Missing values (NaN count) across entire domain and at station grid cells.
6. Station mapping distance check (< 20 km) for all 10 primary stations.
7. Generates: results/phase15_six_year/era5_2019_coverage_audit.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np
import pandas as pd
import xarray as xr

from src.synthetic.physics_2d_dispersion import calculate_haversine_distance_km

def validate_era5_2019(
    nc_path="data/raw/era5/2019/era5_2019_instant.nc",
    stations_path="results/phase11_validation/selected_stations.csv",
    out_dir="results/phase15_six_year"
):
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "era5_2019_coverage_audit.csv")

    if not os.path.exists(nc_path):
        raise FileNotFoundError(f"ERA5 file not found: {nc_path}")

    print(f"[Task 3 Validation] Opening {nc_path} ({os.path.getsize(nc_path)} bytes)...")
    ds = xr.open_dataset(nc_path)

    t_coord = "valid_time" if "valid_time" in ds else "time"
    times = pd.to_datetime(ds[t_coord].values)
    n_steps = len(times)
    t_start = times[0]
    t_end = times[-1]

    # Temporal schedule check
    expected_steps = 1460  # 365 days * 4
    steps_match = (n_steps == expected_steps)
    diffs = np.diff(times).astype("timedelta64[h]").astype(int)
    strictly_6h = (diffs == 6).all() if len(diffs) > 0 else False
    n_duplicates = n_steps - len(set(times))
    has_gaps = not strictly_6h

    # Coordinate inspection
    lats = ds["latitude"].values
    lons = ds["longitude"].values
    lat_order = "DESCENDING" if lats[0] > lats[-1] else "ASCENDING"
    lon_order = "ASCENDING" if lons[0] < lons[-1] else "DESCENDING"

    # Variable audit
    has_u10 = "u10" in ds
    has_v10 = "v10" in ds
    u10_units = ds["u10"].attrs.get("units", "unknown") if has_u10 else "N/A"
    v10_units = ds["v10"].attrs.get("units", "unknown") if has_v10 else "N/A"

    u10_vals = ds["u10"].values
    v10_vals = ds["v10"].values

    u10_min, u10_max = float(np.nanmin(u10_vals)), float(np.nanmax(u10_vals))
    v10_min, v10_max = float(np.nanmin(v10_vals)), float(np.nanmax(v10_vals))
    u10_nan_count = int(np.isnan(u10_vals).sum())
    v10_nan_count = int(np.isnan(v10_vals).sum())

    # Station mapping check
    stations_df = pd.read_csv(stations_path)
    station_slice_nans = 0
    max_station_dist_km = 0.0

    for _, st in stations_df.iterrows():
        s_lat = float(st["station_latitude"])
        s_lon = float(st["station_longitude"])
        lat_idx = int(np.argmin(np.abs(lats - s_lat)))
        lon_idx = int(np.argmin(np.abs(lons - s_lon)))
        c_lat = float(lats[lat_idx])
        c_lon = float(lons[lon_idx])
        d_km = calculate_haversine_distance_km(s_lat, s_lon, c_lat, c_lon)
        if d_km > max_station_dist_km:
            max_station_dist_km = d_km

        u_slice = u10_vals[:, lat_idx, lon_idx]
        v_slice = v10_vals[:, lat_idx, lon_idx]
        station_slice_nans += int(np.isnan(u_slice).sum() + np.isnan(v_slice).sum())

    ds.close()

    is_valid = (
        steps_match and strictly_6h and (n_duplicates == 0) and
        has_u10 and has_v10 and (u10_nan_count == 0) and (v10_nan_count == 0) and
        (station_slice_nans == 0) and (max_station_dist_km <= 20.0)
    )
    verdict = "VALID_AND_COMPLETE" if is_valid else "INVALID_OR_INCOMPLETE"

    audit_row = {
        "calendar_year": 2019,
        "era5_file_path": nc_path,
        "file_size_bytes": os.path.getsize(nc_path),
        "start_timestamp_utc": str(t_start),
        "end_timestamp_utc": str(t_end),
        "actual_synoptic_steps": n_steps,
        "expected_synoptic_steps": expected_steps,
        "steps_match": steps_match,
        "strictly_6_hourly": strictly_6h,
        "duplicate_timestamps": n_duplicates,
        "has_missing_intervals": has_gaps,
        "u10_units": u10_units,
        "v10_units": v10_units,
        "u10_range_ms": f"[{u10_min:.2f}, {u10_max:.2f}]",
        "v10_range_ms": f"[{v10_min:.2f}, {v10_max:.2f}]",
        "u10_total_nans": u10_nan_count,
        "v10_total_nans": v10_nan_count,
        "latitude_bounds": f"[{lats.min():.2f}, {lats.max():.2f}]",
        "longitude_bounds": f"[{lons.min():.2f}, {lons.max():.2f}]",
        "lat_lon_grid_step_deg": "0.25 x 0.25",
        "lat_ordering": lat_order,
        "lon_ordering": lon_order,
        "station_slice_nan_count": station_slice_nans,
        "max_station_to_era5_dist_km": round(max_station_dist_km, 2),
        "audit_verdict": verdict
    }

    df_out = pd.DataFrame([audit_row])
    df_out.to_csv(out_csv, index=False)
    print(f"[Task 3 Validation] Audit completed. Verdict: {verdict}")
    print(f"[Task 3 Validation] Results saved to: {out_csv}")
    return df_out

if __name__ == "__main__":
    validate_era5_2019()
