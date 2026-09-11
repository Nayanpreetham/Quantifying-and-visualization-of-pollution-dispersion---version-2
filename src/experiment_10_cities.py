import os
import pandas as pd
import subprocess
import geopandas as gpd
from shapely.geometry import Point

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

def run_10_cities_experiment():
    print("Running 10 Cities Experiment for 2020-11-01 12:00:00")
    
    print("Cleaning & interpolating OpenAQ data...")
    subprocess.run(['.venv\Scripts\python.exe', 'src/data/cpcb_cleaning.py', '--input', 'data/raw/cpcb/openaq_2020_11_01.csv'])
    subprocess.run(['.venv\Scripts\python.exe', 'src/grid/cpcb_interpolation.py', '--cpcb', 'data/interim/cpcb/cpcb_cleaned.csv'])
    
    print("Generating footprints for target cities (time_idx=12 for 12:00)...")
    subprocess.run(['.venv\Scripts\python.exe', '-m', 'src.physics.footprint_grid', '--meteo', 'data/processed/era5/era5_2020_11.nc', '--time_idx', '12'])
    
    grid = gpd.read_file('data/processed/grid/india_50km_grid.geojson')
    
    target_grids = {}
    for city, coords in CITIES.items():
        pt = gpd.GeoSeries([Point(coords[1], coords[0])], crs='EPSG:4326')
        dist = grid.geometry.distance(pt[0])
        idx = dist.idxmin()
        target_grids[city] = grid.iloc[idx]['grid_id']
        
    print("\nCalculating Contributions...")
    report_lines = ["# 10 Cities Kljun Footprint Experiment\n", "Date: 2020-11-01 12:00:00 UTC\n"]
    
    for city, gid in target_grids.items():
        subprocess.run(['.venv\Scripts\python.exe', 'src/physics/contribution.py', '--target', gid, '--time', '2020-11-01 12:00:00'])
        
        contrib_file = f"data/processed/contributions/contributions_{gid}.csv"
        if os.path.exists(contrib_file):
            df = pd.read_csv(contrib_file)
            
            top_sources = df[df['rank'] <= 5]
            
            report_lines.append(f"## {city} (Target: {gid})")
            if not top_sources.empty:
                report_lines.append(f"- **Wind**: {top_sources.iloc[0]['wind_speed']:.1f} m/s at {top_sources.iloc[0]['wind_direction']:.1f}°")
                report_lines.append("- **Top 5 Contributing Sources:**")
                for _, row in top_sources.iterrows():
                    report_lines.append(f"  - **{row['source_grid_id']}** ({row['distance_km']:.1f} km upstream): {row['contribution_percent']:.1f}%")
            else:
                report_lines.append("- No significant upstream sources detected (or wind too still).")
            report_lines.append("\n")
            
    with open('docs/10_cities_experiment.md', 'w') as f:
        f.write("\n".join(report_lines))
        
    print("Experiment complete. Saved to docs/10_cities_experiment.md")

if __name__ == '__main__':
    run_10_cities_experiment()
