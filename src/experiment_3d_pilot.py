import os
import pandas as pd
import geopandas as gpd
from src.transport.trajectory_model_3d import KinematicTrajectoryModel3D
from src.transport.source_receptor import calculate_trajectory_influence
import warnings
warnings.filterwarnings('ignore')
import xarray as xr

TIMESTAMP = '2020-11-01 12:00:00'
ERA5_3D = 'data/raw/era5/era5_3d_2020_11_01.nc'
ERA5_SFC = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'

CITIES = {
    'Delhi': 'IND_047_021',
    'Mumbai': 'IND_026_012',
    'Varanasi': 'IND_040_032'
}

grid = gpd.read_file(GRID_FILE)
traj_model_3d = KinematicTrajectoryModel3D(ERA5_3D, ERA5_SFC)

# Convert AGL height (m) to hPa roughly using hydrostatic approximation for initialization
# Standard atmosphere: ~1 hPa per 8 meters near surface
def height_to_pressure(height_m, sp_hpa):
    return sp_hpa - (height_m / 8.0)

report = []
report.append("# Mode B: 3D Regional Atmospheric Trajectory Pilot")
report.append(f"Date: {TIMESTAMP} UTC\\n")

for city, gid in CITIES.items():
    print(f"Processing 3D {city}...")
    report.append(f"## {city}")
    
    target_row = grid[grid['grid_id'] == gid].iloc[0]
    lon, lat = target_row.geometry.centroid.x, target_row.geometry.centroid.y
    
    # Get surface pressure
    sp_hpa = float(traj_model_3d.ds_sfc.sel(latitude=lat, longitude=lon, valid_time=TIMESTAMP, method='nearest')['sp'].values) / 100.0
    
    report.append(f"Target Surface Pressure: {sp_hpa:.1f} hPa")
    
    heights_m = [50, 100, 500, 1000]
    
    for h in heights_m:
        p_start = height_to_pressure(h, sp_hpa)
        if p_start < 500:
            continue # Above our ERA5 domain
            
        report.append(f"### Release Height: {h} m AGL (approx {p_start:.1f} hPa)")
        
        for hours in [24, 48, 72]:
            traj_df = traj_model_3d.run_backward_trajectory_3d(lat, lon, p_start, TIMESTAMP, hours=hours, dt_sec=1800)
            
            os.makedirs('data/processed/trajectories_3d', exist_ok=True)
            traj_file = f"data/processed/trajectories_3d/traj_{gid}_{h}m_{hours}h.csv"
            traj_df.to_csv(traj_file, index=False)
            
            influence_df = calculate_trajectory_influence(traj_df, GRID_FILE, gid)
            
            if not influence_df.empty:
                pct_in = influence_df['pct_mass_inside_india'].iloc[0]
                pct_out = influence_df['pct_mass_outside_india'].iloc[0]
                
                dist_max = 111.0 * max(abs(traj_df['latitude'] - lat).max(), abs(traj_df['longitude'] - lon).max())
                
                # Check min pressure (max altitude)
                min_p = traj_df['pressure_hpa'].min()
                
                report.append(f"- **{hours}h**: Max Dist ~{dist_max:.1f} km | Min Pressure {min_p:.1f} hPa | Source Grids: {len(influence_df)} | Indian Domain: {pct_in:.1f}%")
            else:
                report.append(f"- **{hours}h**: No trajectory influence found within grid.")
                
    report.append("\\n")

with open('docs/regional_transport_3d_pilot.md', 'w') as f:
    f.write("\\n".join(report))

print("Done.")
