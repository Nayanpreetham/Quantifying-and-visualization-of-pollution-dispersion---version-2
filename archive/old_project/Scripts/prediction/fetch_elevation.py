"""
Extract elevation at a given lat/lon from india_dem.tif GeoTIFF.
"""

import rasterio
import numpy as np
import os

DEM_PATH = "Raw data/india_dem.tif"

def get_elevation(lat, lon):
    """
    Get elevation in meters at specified coordinates.
    """
    if not os.path.exists(DEM_PATH):
        raise FileNotFoundError(f"DEM file not found: {DEM_PATH}")
    
    with rasterio.open(DEM_PATH) as src:
        row, col = src.index(lon, lat)
        
        if row < 0 or row >= src.height or col < 0 or col >= src.width:
            row = max(0, min(row, src.height - 1))
            col = max(0, min(col, src.width - 1))
        
        elevation = src.read(1)[row, col]
        
        if elevation == src.nodata:
            window = src.read(1, window=((max(0, row-2), min(src.height, row+3)),
                                         (max(0, col-2), min(src.width, col+3))))
            valid = window[window != src.nodata]
            elevation = np.median(valid) if len(valid) > 0 else 0.0
        
        return float(elevation)

if __name__ == "__main__":
    # Test on a few known locations
    test_locations = [
        (28.6139, 77.2090, "Delhi"),
        (19.0760, 72.8777, "Mumbai"),
        (13.0827, 80.2707, "Chennai"),
        (22.5726, 88.3639, "Kolkata"),
        (34.0837, 74.7973, "Srinagar"),
    ]
    
    print("Testing elevation extraction:")
    print("-" * 50)
    for lat, lon, name in test_locations:
        elev = get_elevation(lat, lon)
        print(f"{name:<12} ({lat:.4f}, {lon:.4f}): {elev:.1f} m")