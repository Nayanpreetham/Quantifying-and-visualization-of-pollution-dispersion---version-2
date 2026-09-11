import pandas as pd
import geopandas as gpd
import numpy as np
import argparse
import os
from scipy.spatial import cKDTree

def inverse_distance_weighting(x, y, v, grid_x, grid_y, power=2, max_dist=500000):
    # Custom fast IDW
    tree = cKDTree(np.c_[x, y])
    # Find points within max_dist
    dist, idx = tree.query(np.c_[grid_x, grid_y], k=5, distance_upper_bound=max_dist)
    
    res = np.zeros(len(grid_x))
    station_counts = np.zeros(len(grid_x))
    nearest_dists = np.zeros(len(grid_x))
    
    for i in range(len(grid_x)):
        d = dist[i]
        d = d[d < max_dist]
        valid_idx = idx[i][:len(d)]
        
        station_counts[i] = len(d)
        if len(d) > 0:
            nearest_dists[i] = d[0]
            # Handle exactly zero distance
            if d[0] == 0:
                res[i] = v[valid_idx[0]]
            else:
                w = 1.0 / (d**power)
                res[i] = np.sum(w * v[valid_idx]) / np.sum(w)
        else:
            res[i] = np.nan
            nearest_dists[i] = np.nan
            
    return res, station_counts, nearest_dists

def interpolate_cpcb(cpcb_file, grid_file, output_dir):
    print(f"Interpolating CPCB data to grid...")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, 'cpcb_grid_interpolated.csv')
    
    cpcb = pd.read_csv(cpcb_file)
    grid = gpd.read_file(grid_file)
    
    # Needs metric CRS for accurate IDW distances
    india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    grid_metric = grid.to_crs(india_crs)
    grid_x = grid_metric.geometry.centroid.x.values
    grid_y = grid_metric.geometry.centroid.y.values
    grid_ids = grid_metric['grid_id'].values
    
    # Convert CPCB stations to metric
    # Drop rows without coords
    cpcb = cpcb.dropna(subset=['latitude', 'longitude', 'value'])
    if cpcb.empty:
        print("No valid CPCB data to interpolate.")
        return
        
    cpcb_gdf = gpd.GeoDataFrame(cpcb, geometry=gpd.points_from_xy(cpcb.longitude, cpcb.latitude), crs='EPSG:4326')
    cpcb_metric = cpcb_gdf.to_crs(india_crs)
    
    results = []
    # Interpolate for each timestamp and parameter
    for (dt, param), group in cpcb_metric.groupby(['datetime', 'parameter']):
        x = group.geometry.x.values
        y = group.geometry.y.values
        v = group['value'].values
        
        interp_v, counts, nearest = inverse_distance_weighting(x, y, v, grid_x, grid_y, max_dist=500000) # 500km radius
        
        df_step = pd.DataFrame({
            'grid_id': grid_ids,
            'timestamp': dt,
            'parameter': param,
            'cpcb_interpolated_value': interp_v,
            'station_count': counts,
            'nearest_station_distance': nearest
        })
        
        df_step['interpolation_quality_flag'] = np.where(df_step['cpcb_interpolated_value'].isna(), 'missing', 'valid')
        df_step.loc[(df_step['station_count'] < 2) & (df_step['interpolation_quality_flag'] == 'valid'), 'interpolation_quality_flag'] = 'low_confidence'
        
        results.append(df_step)
        
    final_df = pd.concat(results, ignore_index=True)
    final_df.to_csv(out_file, index=False)
    print(f"Saved interpolated grid data to {out_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cpcb', type=str, default='data/interim/cpcb/cpcb_cleaned.csv')
    parser.add_argument('--grid', type=str, default='data/processed/grid/india_50km_grid.geojson')
    parser.add_argument('--out_dir', type=str, default='data/processed/grid')
    args = parser.parse_args()
    
    interpolate_cpcb(args.cpcb, args.grid, args.out_dir)
