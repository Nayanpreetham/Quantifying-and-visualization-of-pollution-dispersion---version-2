import geopandas as gpd
from shapely.geometry import Polygon, Point
import numpy as np
import os
import math

def generate_india_grid(boundary_file, output_dir, grid_size_km=50):
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, 'india_50km_grid.geojson')
    
    print("Generating India 50km x 50km grid...")
    
    # Load boundary
    india_bounds = gpd.read_file(boundary_file)
    
    # Custom Albers Equal Area Conic for India
    # Standard parallels at 12N and 28N, central meridian at 80E
    india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    
    # Project boundary to metric CRS
    india_metric = india_bounds.to_crs(india_crs)
    
    # Get bounds
    minx, miny, maxx, maxy = india_metric.total_bounds
    
    # Grid size in meters
    step = grid_size_km * 1000
    
    # Create grid cells
    polygons = []
    rows = []
    cols = []
    
    x_coords = np.arange(minx, maxx, step)
    y_coords = np.arange(miny, maxy, step)
    
    for r, y in enumerate(y_coords):
        for c, x in enumerate(x_coords):
            polygons.append(Polygon([(x, y), (x+step, y), (x+step, y+step), (x, y+step)]))
            rows.append(r)
            cols.append(c)
            
    grid = gpd.GeoDataFrame({'row': rows, 'column': cols}, geometry=polygons, crs=india_crs)
    
    # Clip to India boundary
    print("Clipping grid to India boundary...")
    # We use spatial intersection
    grid_clipped = gpd.sjoin(grid, india_metric, how='inner', predicate='intersects').drop(columns=['index_right', 'name'])
    # Optional: true clip geometry -> grid_clipped = gpd.clip(grid, india_metric)
    # But usually for a computational grid, we keep the full square if it intersects.
    # Let's keep full squares that intersect the boundary.
    
    # Calculate properties
    grid_clipped['grid_id'] = [f'IND_{r:03d}_{c:03d}' for r, c in zip(grid_clipped['row'], grid_clipped['column'])]
    grid_clipped['area_km2'] = grid_clipped.geometry.area / 1e6
    
    # Reproject back to WGS84 to get lat/lon centroids
    grid_wgs84 = grid_clipped.to_crs('EPSG:4326')
    grid_wgs84['center_lon'] = grid_wgs84.geometry.centroid.x
    grid_wgs84['center_lat'] = grid_wgs84.geometry.centroid.y
    
    # Ensure unique grid_id
    grid_wgs84 = grid_wgs84.drop_duplicates(subset=['grid_id']).reset_index(drop=True)
    
    # Save
    grid_wgs84.to_file(out_file, driver='GeoJSON')
    print(f"Generated {len(grid_wgs84)} grid cells. Saved to {out_file}")
    
    return grid_wgs84

if __name__ == '__main__':
    generate_india_grid('data/raw/geography/india_boundary.geojson', 'data/processed/grid')
