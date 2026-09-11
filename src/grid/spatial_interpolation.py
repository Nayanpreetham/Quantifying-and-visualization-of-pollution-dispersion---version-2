import pandas as pd
import numpy as np
import xarray as xr
import argparse
import os
from pykrige.ok import OrdinaryKriging
from scipy.interpolate import griddata

def create_continuous_field(cleaned_file, timestamp_str, method='kriging', resolution=0.1, output_dir='data/processed/grid_continuous'):
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"pollution_field_{timestamp_str.replace(':', '').replace('-', '').replace(' ', '_')}.nc")
    
    df = pd.read_csv(cleaned_file)
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    target_dt = pd.to_datetime(timestamp_str)
    if target_dt.tzinfo is None:
        target_dt = target_dt.tz_localize('UTC')
        
    # Get available valid observations for the target time
    time_df = df[(df['datetime'] == target_dt) & (df['quality_flag'] != 'missing')].copy()
    time_df = time_df.dropna(subset=['latitude', 'longitude', 'value'])
    
    # Take median if multiple params exist per station for some reason
    time_df = time_df.groupby(['locationId']).agg({
        'latitude': 'first',
        'longitude': 'first',
        'value': 'median'
    }).reset_index()
    
    print(f"Generating field for {target_dt} using {len(time_df)} valid stations.")
    
    if len(time_df) < 5:
        print("Warning: Too few stations for robust interpolation. Interpolation might fail or be trivial.")
        
    # India bounding box
    lat_min, lat_max = 6.0, 38.0
    lon_min, lon_max = 68.0, 98.0
    
    grid_lons = np.arange(lon_min, lon_max + resolution, resolution)
    grid_lats = np.arange(lat_min, lat_max + resolution, resolution)
    
    lons = time_df['longitude'].values
    lats = time_df['latitude'].values
    vals = time_df['value'].values
    
    grid_z = np.full((len(grid_lats), len(grid_lons)), np.nan)
    variance_z = np.full((len(grid_lats), len(grid_lons)), np.nan)
    
    if len(time_df) >= 3:
        if method == 'kriging':
            try:
                # Ordinary Kriging
                OK = OrdinaryKriging(
                    lons, lats, vals,
                    variogram_model='spherical',
                    verbose=False,
                    enable_plotting=False,
                    coordinates_type='geographic'
                )
                z, ss = OK.execute('grid', grid_lons, grid_lats)
                grid_z = z.data
                variance_z = ss.data
            except Exception as e:
                print(f"Kriging failed: {e}. Falling back to IDW.")
                method = 'idw'
                
        if method == 'idw':
            grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lons, grid_lats)
            # Standard griddata interpolation (linear/nearest)
            grid_z = griddata((lons, lats), vals, (grid_lon_mesh, grid_lat_mesh), method='linear')
            
            # For NaNs outside hull, use nearest
            nan_mask = np.isnan(grid_z)
            if np.any(nan_mask):
                nearest_z = griddata((lons, lats), vals, (grid_lon_mesh, grid_lat_mesh), method='nearest')
                grid_z[nan_mask] = nearest_z[nan_mask]
                
            variance_z = np.full_like(grid_z, 1.0) # Dummy uncertainty for IDW
            
    # Calculate nearest station distance for each grid point
    # Rough Euclidean distance in degrees for simplicity in diagnostics
    grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lons, grid_lats)
    nearest_dist = np.full_like(grid_lon_mesh, np.nan)
    if len(lons) > 0:
        for i in range(len(grid_lats)):
            for j in range(len(grid_lons)):
                dist = np.sqrt((lons - grid_lon_mesh[i,j])**2 + (lats - grid_lat_mesh[i,j])**2)
                nearest_dist[i,j] = np.min(dist)
    
    # Store in xarray
    ds = xr.Dataset(
        {
            "AQI": (["lat", "lon"], grid_z),
            "uncertainty": (["lat", "lon"], variance_z),
            "nearest_station_dist_deg": (["lat", "lon"], nearest_dist)
        },
        coords={
            "lon": grid_lons,
            "lat": grid_lats
        },
        attrs={
            "description": "Continuous Spatial Interpolation Field",
            "method": method,
            "resolution_deg": resolution,
            "timestamp": str(target_dt)
        }
    )
    
    ds.to_netcdf(out_file)
    print(f"Saved continuous field to {out_file}")
    return out_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help="Cleaned CPCB CSV")
    parser.add_argument('--time', type=str, required=True, help="Target timestamp (e.g., '2020-11-01 12:00:00')")
    parser.add_argument('--method', type=str, default='kriging', choices=['kriging', 'idw'])
    parser.add_argument('--resolution', type=float, default=0.1)
    args = parser.parse_args()
    
    create_continuous_field(args.input, args.time, args.method, args.resolution)
