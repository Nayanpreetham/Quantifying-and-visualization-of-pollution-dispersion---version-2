import geopandas as gpd
import xarray as xr
import pandas as pd
import argparse
import os
from shapely.geometry import Point

def aggregate_to_50km_grid(continuous_field_file, grid_geojson='data/processed/grid/india_50km_grid.geojson', output_dir='data/processed/grid_aggregated'):
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading continuous field: {continuous_field_file}")
    ds = xr.open_dataset(continuous_field_file)
    df = ds.to_dataframe().reset_index()
    df = df.dropna(subset=['AQI'])
    
    # Create GeoDataFrame of continuous points
    geometry = [Point(xy) for xy in zip(df['lon'], df['lat'])]
    gdf_points = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
    
    print(f"Loading 50km grid: {grid_geojson}")
    grid = gpd.read_file(grid_geojson)
    if grid.crs != 'EPSG:4326':
        grid = grid.to_crs('EPSG:4326')
        
    print("Performing spatial join (Continuous Field -> 50km Polygons)...")
    joined = gpd.sjoin(gdf_points, grid, how='inner', predicate='within')
    
    # Area-weighted aggregation (since points are uniform 0.1x0.1 deg, simple mean is mathematically equivalent to area-weighted)
    aggregated = joined.groupby('grid_id').agg(
        cell_AQI=('AQI', 'mean'),
        cell_median=('AQI', 'median'),
        cell_std=('AQI', 'std'),
        number_of_valid_fine_pixels=('AQI', 'count'),
        interpolation_uncertainty=('uncertainty', 'mean')
    ).reset_index()
    
    # Merge back to grid to preserve all cells (even empty ones)
    final_grid = grid[['grid_id', 'geometry']].merge(aggregated, on='grid_id', how='left')
    
    # Calculate centroids
    final_grid['centroid_lon'] = final_grid.geometry.centroid.x
    final_grid['centroid_lat'] = final_grid.geometry.centroid.y
    
    out_file = os.path.join(output_dir, f"aggregated_50km_{pd.to_datetime(ds.attrs['timestamp']).strftime('%Y%m%d_%H%M%S')}.geojson")
    
    final_grid.to_file(out_file, driver='GeoJSON')
    
    csv_file = out_file.replace('.geojson', '.csv')
    final_grid.drop(columns=['geometry']).to_csv(csv_file, index=False)
    
    print(f"Saved aggregated 50km grid to {out_file} and {csv_file}")
    return csv_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help="Continuous Field NetCDF")
    parser.add_argument('--grid', type=str, default='data/processed/grid/india_50km_grid.geojson')
    args = parser.parse_args()
    
    aggregate_to_50km_grid(args.input, args.grid)
