"""
PHASE 13: INITIAL INVENTORY SCRIPT
==================================
Inspects all real observation and meteorological datasets on disk.
"""

import os
import sys
import glob
import pandas as pd
import xarray as xr

def inspect_all():
    print("=== 1. OPENAQ PM2.5 DATASETS ===")
    obs_files = glob.glob("data/real/openaq/*.csv") + glob.glob("data/raw/openaq/*.csv")
    for f in obs_files:
        sz_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"\nObservation File: {f} ({sz_mb:.2f} MB)")
        try:
            df = pd.read_csv(f, nrows=1000)
            print(f"  Columns: {list(df.columns)}")
        except Exception as e:
            print(f"  Error reading sample: {e}")

    main_obs = "data/real/openaq/pm25_observations.csv"
    if os.path.exists(main_obs):
        print(f"\n--- Deep Inspection of {main_obs} ---")
        df_obs = pd.read_csv(main_obs)
        print(f"Total rows: {len(df_obs):,}")
        df_obs["dt"] = pd.to_datetime(df_obs["timestamp_utc"]).dt.tz_localize(None)
        print(f"Min timestamp: {df_obs['dt'].min()}")
        print(f"Max timestamp: {df_obs['dt'].max()}")
        df_obs["year"] = df_obs["dt"].dt.year
        df_obs["month"] = df_obs["dt"].dt.to_period("M")
        
        yearly = df_obs.groupby("year").agg(
            obs_count=("pm25", "count"),
            station_count=("station_id", "nunique"),
            min_date=("dt", "min"),
            max_date=("dt", "max")
        ).reset_index()
        print("\nYearly summary:")
        print(yearly.to_string(index=False))

    print("\n=== 2. ERA5 NETCDF METEOROLOGY FILES ===")
    nc_patterns = [
        "data/raw/era5/*.nc",
        "data/raw/era5/**/*.nc",
        "data/processed/era5/*.nc",
        "data/national/*.nc",
        "data/regional/*.nc",
        "data/real/era5/*.nc"
    ]
    all_nc = []
    for pat in nc_patterns:
        all_nc.extend(glob.glob(pat, recursive=True))
    all_nc = sorted(list(set(all_nc)))

    print(f"Found {len(all_nc)} NetCDF files.")
    for f in all_nc:
        sz_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"\nNetCDF File: {f} ({sz_mb:.2f} MB)")
        try:
            ds = xr.open_dataset(f)
            vars_list = list(ds.data_vars.keys())
            dims = dict(ds.dims)
            t_col = None
            for c in ["time", "valid_time", "forecast_reference_time"]:
                if c in ds.coords or c in ds.dims:
                    t_col = c
                    break
            
            t_info = "No time coord"
            if t_col:
                times = ds[t_col].values
                t_info = f"{str(times[0])[:19]} to {str(times[-1])[:19]} (N={len(times)})"
            
            lat_col = "latitude" if "latitude" in ds.coords else ("lat" if "lat" in ds.coords else None)
            lon_col = "longitude" if "longitude" in ds.coords else ("lon" if "lon" in ds.coords else None)
            geo_info = ""
            if lat_col and lon_col:
                geo_info = f" | Lat: [{float(ds[lat_col].min()):.2f}, {float(ds[lat_col].max()):.2f}], Lon: [{float(ds[lon_col].min()):.2f}, {float(ds[lon_col].max()):.2f}]"

            print(f"  Variables: {vars_list}")
            print(f"  Time: {t_info}{geo_info}")
            ds.close()
        except Exception as e:
            print(f"  Error opening: {e}")

if __name__ == "__main__":
    inspect_all()
