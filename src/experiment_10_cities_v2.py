import os
import subprocess
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import glob

print("Running 10 Cities Experiment (V2 - Continuous Field Architecture) for 2020-11-01 12:00:00")

TIMESTAMP = '2020-11-01 12:00:00'
CLEANED_DATA = 'data/interim/cpcb/cpcb_cleaned.csv'
ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'

# 1. Clean Data
subprocess.run(['.venv\Scripts\python.exe', 'src/data/cpcb_cleaning.py', '--input', 'data/raw/cpcb/openaq_2020_11_01.csv'])

# 2. Continuous Spatial Interpolation
subprocess.run(['.venv\Scripts\python.exe', 'src/grid/spatial_interpolation.py', '--input', CLEANED_DATA, '--time', TIMESTAMP, '--method', 'kriging'])

# Find the generated netcdf file
nc_files = glob.glob('data/processed/grid_continuous/*.nc')
nc_files.sort(key=os.path.getmtime, reverse=True)
latest_nc = nc_files[0]

# 3. Aggregation to 50km
subprocess.run(['.venv\Scripts\python.exe', 'src/grid/grid_aggregation.py', '--input', latest_nc, '--grid', GRID_FILE])

agg_files = glob.glob('data/processed/grid_aggregated/*.csv')
agg_files.sort(key=os.path.getmtime, reverse=True)
latest_agg = agg_files[0]

# 4. Process Target Cities
CITIES = {
    'Delhi': (28.6139, 77.2090),
    'Lucknow': (26.8467, 80.9462),
    'Varanasi': (25.3176, 82.9739),
    'Kanpur': (26.4499, 80.3319),
    'Patna': (25.5941, 85.1376),
    'Kolkata': (22.5726, 88.3639),
    'Mumbai': (19.0760, 72.8777),
    'Ahmedabad': (23.0225, 72.5714),
    'Hyderabad': (17.3850, 78.4867),
    'Bengaluru': (12.9716, 77.5946)
}

grid = gpd.read_file(GRID_FILE)
target_grids = {}
for city, coords in CITIES.items():
    pt = gpd.GeoSeries([Point(coords[1], coords[0])], crs='EPSG:4326')
    dist = grid.geometry.distance(pt[0])
    idx = dist.idxmin()
    target_grids[city] = grid.iloc[idx]['grid_id']

report_lines = ["# 10 Cities Continuous-Field Validation\n", f"Date: {TIMESTAMP} UTC\n"]

for city, gid in target_grids.items():
    print(f"\nProcessing {city} ({gid})...")
    # Footprint
    subprocess.run(['.venv\Scripts\python.exe', '-m', 'src.physics.footprint_continuous', '--target', gid, '--grid', GRID_FILE, '--meteo', ERA5_DATA, '--time_idx', TIMESTAMP])
    
    fp_file = f"data/processed/footprints/footprint_weights_{gid}.csv"
    
    # Contribution
    if os.path.exists(fp_file):
        subprocess.run(['.venv\Scripts\python.exe', 'src/physics/contribution.py', '--target', gid, '--time', TIMESTAMP, '--footprint', fp_file, '--cpcb_aggregated', latest_agg])
        
        contrib_file = f"data/processed/contributions/contributions_{gid}.csv"
        df = pd.read_csv(contrib_file)
        
        top_sources = df[df['rank'] <= 5]
        pct_outside = df['pct_mass_outside_domain'].iloc[0] if 'pct_mass_outside_domain' in df.columns else 0.0
        
        report_lines.append(f"## {city} (Target: {gid})")
        report_lines.append(f"- **Wind**: {top_sources.iloc[0]['wind_speed']:.1f} m/s at {top_sources.iloc[0]['wind_direction']:.1f}°")
        report_lines.append(f"- **Footprint Domain Loss**: {pct_outside:.1f}% outside India")
        report_lines.append("- **Top 5 Contributing Sources:**")
        if not top_sources.empty:
            for _, row in top_sources.iterrows():
                report_lines.append(f"  - **{row['source_grid_id']}** ({row['distance_km']:.1f} km upstream, AQI: {row['baseline_pollution_indicator']:.1f}): {row['contribution_percent']:.1f}%")
        else:
            report_lines.append("- No significant upstream sources detected (or wind too still).")
        report_lines.append("\n")

with open('docs/10_cities_experiment_v2.md', 'w') as f:
    f.write("\n".join(report_lines))

print("\nExperiment complete. Saved to docs/10_cities_experiment_v2.md")
