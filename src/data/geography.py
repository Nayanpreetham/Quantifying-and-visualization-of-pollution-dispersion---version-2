import geopandas as gpd
from shapely.geometry import Polygon
import os

def get_india_boundary(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, 'india_boundary.geojson')
    
    if os.path.exists(out_file):
        print(f"File {out_file} already exists.")
        return out_file
        
    print("Generating India bounding box GeoJSON...")
    # Rough bounding box for India for testing purposes
    # minx, miny, maxx, maxy = 68.0, 6.75, 97.5, 37.5
    poly = Polygon([(68.0, 6.75), (97.5, 6.75), (97.5, 37.5), (68.0, 37.5), (68.0, 6.75)])
    gdf = gpd.GeoDataFrame([{'name': 'India'}], geometry=[poly], crs="EPSG:4326")
    
    gdf.to_file(out_file, driver='GeoJSON')
    print(f"Saved India boundary to {out_file}")
    return out_file

if __name__ == '__main__':
    get_india_boundary('data/raw/geography')
