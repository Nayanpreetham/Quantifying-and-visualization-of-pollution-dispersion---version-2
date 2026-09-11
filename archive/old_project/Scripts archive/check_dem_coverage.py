import rasterio
import pandas as pd
import numpy as np
import os
from rasterio.sample import sample_gen

PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
OUTPUT_FOLDER = os.path.join(PROJECT, "output")
DEM_FILE = os.path.join(PROJECT, "india_dem.tif")

# Load cities
df = pd.read_csv(os.path.join(OUTPUT_FOLDER, "aqi_era5_merged.csv"))
cities = df[['city', 'lat', 'lon']].drop_duplicates().reset_index(drop=True)

print("Analyzing DEM Coverage...")
print("=" * 50)

with rasterio.open(DEM_FILE) as dem:
    print(f"\nDEM Info:")
    print(f"  CRS: {dem.crs}")
    print(f"  Bounds: {dem.bounds}")
    print(f"  Resolution: {dem.res}")
    print(f"  Width x Height: {dem.width} x {dem.height}")
    print(f"  Total pixels: {dem.width * dem.height:,}")
    
    # Count valid data pixels
    band = dem.read(1)
    valid_pixels = np.sum(~np.isnan(band) & (band != dem.nodata))
    print(f"  Valid pixels: {valid_pixels:,} ({valid_pixels/(dem.width*dem.height)*100:.1f}%)")
    
    # Extract elevations for all cities
    coverage = []
    elevations = []
    
    for idx, row in cities.iterrows():
        lon, lat = row['lon'], row['lat']
        
        try:
            # Sample elevation
            samples = list(sample_gen(dem, [(lon, lat)]))
            elev = samples[0][0]
            
            # Check if valid (not nodata)
            is_valid = not (elev is None or np.isnan(elev) or elev == dem.nodata or elev < -1000)
            
            coverage.append(is_valid)
            elevations.append(elev if is_valid else np.nan)
            
        except Exception as e:
            coverage.append(False)
            elevations.append(np.nan)
    
    cities['has_elevation'] = coverage
    cities['elevation_m'] = elevations

# Coverage statistics
total_cities = len(cities)
covered_cities = cities['has_elevation'].sum()
missing_cities = total_cities - covered_cities

print(f"\n📊 City Coverage:")
print(f"  Total cities: {total_cities}")
print(f"  Cities with DEM data: {covered_cities} ({covered_cities/total_cities*100:.1f}%)")
print(f"  Cities without DEM data: {missing_cities} ({missing_cities/total_cities*100:.1f}%)")

if missing_cities > 0:
    print(f"\n⚠ Cities WITHOUT elevation data:")
    missing_list = cities[~cities['has_elevation']]['city'].tolist()
    for i, city in enumerate(missing_list[:10]):  # Show first 10
        print(f"    - {city}")
    if len(missing_list) > 10:
        print(f"    ... and {len(missing_list)-10} more")

# Save coverage info
cities[['city', 'lat', 'lon', 'has_elevation', 'elevation_m']].to_csv(
    os.path.join(OUTPUT_FOLDER, "dem_coverage_check.csv"), index=False
)
print(f"\n✅ Coverage check saved to: {OUTPUT_FOLDER}/dem_coverage_check.csv")