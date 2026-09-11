import pandas as pd
import numpy as np
import os
import warnings
import argparse
warnings.filterwarnings('ignore')

try:
    from pykrige.ok import OrdinaryKriging
except ImportError:
    print("Installing pykrige...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pykrige", "xarray", "netCDF4"])
    from pykrige.ok import OrdinaryKriging

def interpolate_kriging(input_csv, out_nc):
    print(f"Loading point data from {input_csv}...")
    df = pd.read_csv(input_csv)
    
    # Domain matching India extended bounding box
    # 5 to 38 N, 68 to 98 E
    # Resolution: 0.1 degree (~10km) as requested for the continuous spatial field
    grid_lon = np.arange(68.0, 98.1, 0.1)
    grid_lat = np.arange(5.0, 38.1, 0.1)
    
    print(f"Creating continuous spatial grid: {len(grid_lat)} lats x {len(grid_lon)} lons = {len(grid_lat)*len(grid_lon)} pixels")
    
    lons = df['lon'].values
    lats = df['lat'].values
    vals = df['pm25'].values
    
    print(f"Running Ordinary Kriging on {len(vals)} coordinate points...")
    print("Note: Names/metadata are strictly excluded. Operating purely on spatial coordinates.")
    
    # Spherical variogram model is typically robust for regional pollution
    # nlags=20 provides good empirical variogram binning
    OK = OrdinaryKriging(
        lons, lats, vals,
        variogram_model='spherical',
        verbose=False,
        enable_plotting=False,
        nlags=20
    )
    
    # Execute on the regular grid
    print("Executing kriging interpolation over grid (this may take a minute)...")
    z, ss = OK.execute('grid', grid_lon, grid_lat)
    
    print("Kriging complete. Converting to NetCDF spatial field...")
    import xarray as xr
    
    ds = xr.Dataset(
        {
            "pm25": (["latitude", "longitude"], z.data),
            "kriging_variance": (["latitude", "longitude"], ss.data)
        },
        coords={
            "longitude": grid_lon,
            "latitude": grid_lat,
        }
    )
    
    os.makedirs(os.path.dirname(out_nc), exist_ok=True)
    ds.to_netcdf(out_nc)
    print(f"\nSaved continuous interpolated field to {out_nc}")
    
    # Print statistics of the interpolated field
    print(f"Spatial Field Stats -> Min: {np.nanmin(z.data):.1f}, Max: {np.nanmax(z.data):.1f}, Mean: {np.nanmean(z.data):.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Perform spatial interpolation via Kriging')
    parser.add_argument('--input', type=str, default='data/raw/openaq/spatial_pm25_2020-11-01.csv')
    parser.add_argument('--output', type=str, default='data/processed/grid/kriged_pm25_20201101.nc')
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Input file {args.input} not found. Ensure the fetch script has completed.")
    else:
        interpolate_kriging(args.input, args.output)
