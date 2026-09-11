import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
import argparse
import os
from src.physics.kljun import kljun_ffp
import math
from shapely.geometry import Point

def calculate_continuous_footprint(target_grid_id, grid_file, meteo_file, output_dir, time_idx=0):
    print(f"Calculating Continuous Kljun footprint for {target_grid_id}...")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f'footprint_weights_{target_grid_id}.csv')
    
    grid = gpd.read_file(grid_file)
    ds = xr.open_dataset(meteo_file)
    
    if isinstance(time_idx, str):
        t = pd.to_datetime(time_idx)
        ds_t = ds.sel(valid_time=t)
    else:
        t = ds.valid_time.values[time_idx]
        ds_t = ds.sel(valid_time=t)
    
    india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    grid_metric = grid.to_crs(india_crs)
    
    target_row = grid_metric[grid_metric['grid_id'] == target_grid_id].iloc[0]
    
    cx_t = target_row.geometry.centroid.x
    cy_t = target_row.geometry.centroid.y
    cx_deg = target_row['center_lon']
    cy_deg = target_row['center_lat']
    
    try:
        m = ds_t.sel(longitude=cx_deg, latitude=cy_deg, method='nearest')
    except KeyError:
        print(f"Meteorology missing for {target_grid_id}")
        return
        
    wd = float(m['wind_direction'].values)
    ws = float(m['wind_speed'].values)
    u_star = float(m['u_star'].values)
    L = float(m['L'].values)
    sigma_v = float(m['sigma_v'].values)
    blh = float(m['pblh'].values)
    
    # Kljun footprint for 10m receptor is concentrated within 1-10km.
    # We use a 100km radius mesh at 200m resolution to capture it accurately.
    max_dist = 100000.0 # 100 km
    res = 200.0 # 200m resolution
    
    xs = np.arange(-max_dist, max_dist, res)
    ys = np.arange(-max_dist, max_dist, res)
    xx, yy = np.meshgrid(xs, ys)
    
    grid_x = cx_t + xx
    grid_y = cy_t + yy
    
    # Correct wind orientation: vector pointing UPWIND
    wd_rad = math.radians((90 - wd) % 360)
    cos_wd = math.cos(wd_rad)
    sin_wd = math.sin(wd_rad)
    
    # Kljun x_rot is distance upwind.
    x_rot = xx * cos_wd + yy * sin_wd
    y_rot = -xx * sin_wd + yy * cos_wd
    
    zm = 10.0
    z0 = 0.1
    
    f, flag = kljun_ffp(zm, z0, ws, blh, L, sigma_v, u_star, x_rot, y_rot)
    
    f[np.isnan(f)] = 0
    f[f < 0] = 0
    
    total_mass_generated = np.sum(f) * (res * res)
    
    valid_mask = f > 1e-12
    v_x = grid_x[valid_mask]
    v_y = grid_y[valid_mask]
    v_f = f[valid_mask]
    
    if len(v_f) == 0:
        print("Footprint generated 0 mass.")
        return
        
    points = gpd.points_from_xy(v_x, v_y, crs=india_crs)
    fp_gdf = gpd.GeoDataFrame({'f_density': v_f}, geometry=points, crs=india_crs)
    
    # To save memory, only sjoin with grid cells near the target
    # Get bounding box of valid footprint
    xmin, ymin, xmax, ymax = fp_gdf.total_bounds
    nearby_grids = grid_metric.cx[xmin:xmax, ymin:ymax]
    
    joined = gpd.sjoin(fp_gdf, nearby_grids[['grid_id', 'geometry']], how='left', predicate='within')
    
    joined['mass'] = joined['f_density'] * (res * res)
    
    inside = joined.dropna(subset=['grid_id'])
    outside = joined[joined['grid_id'].isna()]
    
    mass_inside = inside['mass'].sum()
    mass_outside = outside['mass'].sum()
    
    if total_mass_generated > 0:
        pct_inside = (mass_inside / total_mass_generated) * 100.0
        pct_outside = (mass_outside / total_mass_generated) * 100.0
    else:
        pct_inside = 0
        pct_outside = 0
        
    print(f"Footprint Mass Inside Domain: {pct_inside:.2f}%, Outside Domain: {pct_outside:.2f}%")
    
    source_mass = inside.groupby('grid_id')['mass'].sum().reset_index()
    source_mass['footprint_normalized'] = source_mass['mass'] / mass_inside if mass_inside > 0 else 0
    
    source_mass['target_grid_id'] = target_grid_id
    source_mass['timestamp'] = t
    source_mass['wind_speed'] = ws
    source_mass['wind_direction'] = wd
    source_mass['PBLH'] = blh
    source_mass['stability_L'] = L
    source_mass['pct_mass_outside_domain'] = pct_outside
    
    source_geoms = grid_metric.set_index('grid_id').loc[source_mass['grid_id'], 'geometry']
    dist = source_geoms.centroid.distance(target_row.geometry.centroid).values / 1000.0
    source_mass['distance_km'] = dist
    source_mass = source_mass.rename(columns={'grid_id': 'source_grid_id', 'mass': 'footprint_weight'})
    
    source_mass.to_csv(out_file, index=False)
    print(f"Saved footprint weights to {out_file}")
    
    return out_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=str, required=True)
    parser.add_argument('--grid', type=str, default='data/processed/grid/india_50km_grid.geojson')
    parser.add_argument('--meteo', type=str, default='data/processed/era5/era5_2020_11.nc')
    parser.add_argument('--out_dir', type=str, default='data/processed/footprints')
    parser.add_argument('--time_idx', type=str, default="0")
    args = parser.parse_args()
    
    if args.time_idx.isdigit():
        args.time_idx = int(args.time_idx)
        
    calculate_continuous_footprint(args.target, args.grid, args.meteo, args.out_dir, args.time_idx)
