import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
import argparse
import os
from .kljun import kljun_ffp
import math

def calculate_grid_footprint(grid_file, meteo_file, output_dir, time_idx=0):
    print("Calculating Kljun grid-to-grid footprint...")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, 'footprint_weights.csv')
    
    grid = gpd.read_file(grid_file)
    ds = xr.open_dataset(meteo_file)
    
    # We will pick one timestamp for demonstration/testing
    t = ds.valid_time.values[time_idx]
    ds_t = ds.sel(valid_time=t)
    
    # Needs metric CRS to compute distances in meters
    india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    grid_metric = grid.to_crs(india_crs)
    
    cx = grid_metric.geometry.centroid.x.values
    cy = grid_metric.geometry.centroid.y.values
    gids = grid_metric['grid_id'].values
    
    # To map grid cells to ERA5 lat/lon, we use the WGS84 centroids
    cx_deg = grid['center_lon'].values
    cy_deg = grid['center_lat'].values
    
    results = []
    
    for i in range(len(gids)):
        target_id = gids[i]
        
        # Get meteorology at target location
        # Find nearest ERA5 grid point
        try:
            m = ds_t.sel(longitude=cx_deg[i], latitude=cy_deg[i], method='nearest')
        except KeyError:
            continue
            
        wd = float(m['wind_direction'].values)
        ws = float(m['wind_speed'].values)
        u_star = float(m['u_star'].values)
        L = float(m['L'].values)
        sigma_v = float(m['sigma_v'].values)
        blh = float(m['pblh'].values)
        
        # Wind rotation to orient x along wind direction
        wd_rad = math.radians((270 - wd) % 360) # math angle
        cos_wd = math.cos(wd_rad)
        sin_wd = math.sin(wd_rad)
        
        # Distances to all other grids
        dx = cx - cx[i]
        dy = cy - cy[i]
        
        # Rotate coordinates
        x_rot = dx * cos_wd + dy * sin_wd
        y_rot = -dx * sin_wd + dy * cos_wd
        
        # Calculate footprint for all source grids
        # Receptor height zm = 10m (effective height of city)
        zm = 10.0
        z0 = 0.1
        
        f, flag = kljun_ffp(zm, z0, ws, blh, L, sigma_v, u_star, x_rot, y_rot)
        
        # Filter sources with significant footprint
        valid_idx = np.where(f > 1e-12)[0]
        
        if len(valid_idx) == 0:
            continue
            
        # Normalize weights to sum to 1 for this target (relative contribution)
        f_valid = f[valid_idx]
        total_f = np.sum(f_valid)
        norm_weights = f_valid / total_f
        
        df_target = pd.DataFrame({
            'target_grid_id': target_id,
            'source_grid_id': gids[valid_idx],
            'timestamp': t,
            'footprint_weight': f_valid,
            'footprint_normalized': norm_weights,
            'distance_km': np.sqrt(dx[valid_idx]**2 + dy[valid_idx]**2) / 1000.0,
            'wind_speed': ws,
            'wind_direction': wd,
            'PBLH': blh,
            'stability_L': L,
            'quality_flag': flag
        })
        results.append(df_target)
        
    if results:
        final_df = pd.concat(results, ignore_index=True)
        final_df.to_csv(out_file, index=False)
        print(f"Saved footprint weights for {len(results)} targets to {out_file}")
    else:
        print("No valid footprints calculated.")
        
    ds.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--grid', type=str, default='data/processed/grid/india_50km_grid.geojson')
    parser.add_argument('--meteo', type=str, default='data/processed/era5/era5_2020_01.nc')
    parser.add_argument('--out_dir', type=str, default='data/processed/footprints')
    parser.add_argument('--time_idx', type=int, default=0)
    args = parser.parse_args()
    
    calculate_grid_footprint(args.grid, args.meteo, args.out_dir, args.time_idx)
