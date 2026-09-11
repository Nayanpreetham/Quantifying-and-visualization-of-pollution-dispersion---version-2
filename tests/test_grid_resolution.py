import geopandas as gpd
import numpy as np
import sys

def test_grid_resolution():
    try:
        grid = gpd.read_file('data/processed/grid/india_50km_grid.geojson')
    except Exception as e:
        print("Grid file not found.")
        sys.exit(1)
        
    # Project to metric CRS to calculate width/height accurately
    india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    grid_metric = grid.to_crs(india_crs)
    
    # Calculate bounding box dimensions for each cell
    bounds = grid_metric.bounds
    widths = (bounds.maxx - bounds.minx) / 1000.0
    heights = (bounds.maxy - bounds.miny) / 1000.0
    areas = grid_metric.geometry.area / 1e6
    
    mean_w = widths.mean()
    mean_h = heights.mean()
    mean_area = areas.mean()
    
    print("GRID RESOLUTION AUDIT:")
    print(f"Total Cells: {len(grid)}")
    print(f"Mean Width: {mean_w:.2f} km (Min: {widths.min():.2f}, Max: {widths.max():.2f})")
    print(f"Mean Height: {mean_h:.2f} km (Min: {heights.min():.2f}, Max: {heights.max():.2f})")
    print(f"Mean Area: {mean_area:.2f} km^2 (Min: {areas.min():.2f}, Max: {areas.max():.2f})")
    
    # Tolerances
    assert 48 < widths.max() < 52, f"Max width {widths.max()} is not ~50km"
    assert 48 < heights.max() < 52, f"Max height {heights.max()} is not ~50km"
    print("ALL GRID TESTS PASSED")

if __name__ == '__main__':
    try:
        test_grid_resolution()
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
