import os
import sys
import pandas as pd
import datetime
import cdsapi
import glob
import warnings
warnings.filterwarnings('ignore')

from src.transport.trajectory_model_3d import KinematicTrajectoryModel3D
from src.transport.ensemble_model import EnsembleTrajectoryModel
from src.transport.source_receptor import calculate_ensemble_influence

CITIES = {
    'Delhi': 'IND_047_021',
    'Lucknow': 'IND_043_028',
    'Varanasi': 'IND_040_032',
    'Kanpur': 'IND_042_027',
    'Patna': 'IND_041_037',
    'Kolkata': 'IND_034_043',
    'Mumbai': 'IND_026_012',
    'Ahmedabad': 'IND_035_011',
    'Hyderabad': 'IND_022_023',
    'Bengaluru': 'IND_012_021'
}

HEIGHTS_M = [50, 100, 500]
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'

def download_era5_chunk(year, month, out_file):
    if os.path.exists(out_file):
        return True
        
    c = cdsapi.Client()
    
    # Calculate days in month
    import calendar
    _, num_days = calendar.monthrange(year, month)
    days = [f"{d:02d}" for d in range(1, num_days + 1)]
    
    try:
        c.retrieve(
            'reanalysis-era5-pressure-levels',
            {
                'product_type': 'reanalysis',
                'format': 'netcdf',
                'variable': [
                    'u_component_of_wind', 'v_component_of_wind', 'vertical_velocity'
                ],
                'pressure_level': ['500', '700', '850', '925', '1000'],
                'year': str(year),
                'month': f"{month:02d}",
                'day': days,
                'time': ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
                'area': [35, 68, 15, 90],
            },
            out_file
        )
        return True
    except Exception as e:
        print(f"CDS Download Failed: {e}")
        return False

def height_to_pressure(height_m, sp_hpa):
    return sp_hpa - (height_m / 8.0)

def process_month(year, month):
    print(f"\\n======================================")
    print(f"Processing {year}-{month:02d}")
    
    era5_3d_file = f"data/raw/era5/era5_3d_{year}_{month:02d}.nc"
    
    # NOTE: We assume the 2D surface file (for Surface Pressure) and 
    # CPCB continuous fields are already processed for this month by other pipelines.
    # For this script, we assume era5_surface exists.
    era5_sfc_file = f"data/processed/era5/era5_{year}_{month:02d}.nc"
    if not os.path.exists(era5_sfc_file):
        print(f"Warning: Surface file {era5_sfc_file} missing. Skipping month.")
        return
        
    # 1. Download
    print("1. Downloading 3D ERA5...")
    # download_era5_chunk(year, month, era5_3d_file) # Uncomment for actual run
    
    if not os.path.exists(era5_3d_file):
        print(f"Failed to obtain 3D data for {year}-{month:02d}")
        return
        
    # 2. Process Trajectories
    print("2. Initializing 3D RK4 Engine...")
    import geopandas as gpd
    grid = gpd.read_file(GRID_FILE)
    traj_model = KinematicTrajectoryModel3D(era5_3d_file, era5_sfc_file)
    
    # We would loop over every day/hour here. For demonstration, just one timestamp
    timestamps = [f"{year}-{month:02d}-01 12:00:00"] 
    
    for ts in timestamps:
        print(f"   -> Timestamp {ts}")
        
        for city, gid in CITIES.items():
            target_row = grid[grid['grid_id'] == gid].iloc[0]
            lon, lat = target_row.geometry.centroid.x, target_row.geometry.centroid.y
            
            try:
                sp_hpa = float(traj_model.ds_sfc.sel(latitude=lat, longitude=lon, valid_time=ts, method='nearest')['sp'].values) / 100.0
            except:
                continue
                
            for h in HEIGHTS_M:
                p_start = height_to_pressure(h, sp_hpa)
                if p_start < 500: continue
                
                # run trajectory
                traj_df = traj_model.run_backward_trajectory_3d(lat, lon, p_start, ts, hours=72, dt_sec=1800)
                
                # compute influence matrix T_ij
                influence_df = calculate_trajectory_influence(traj_df, GRID_FILE, gid)
                
                if not influence_df.empty:
                    os.makedirs('data/processed/matrices', exist_ok=True)
                    out_f = f"data/processed/matrices/T_{gid}_{h}m_{ts.replace(':','').replace('-','').replace(' ','_')}.csv"
                    influence_df.to_csv(out_f, index=False)
                    
                    # Compute C_ij if continuous field exists... (Skipped in this template)
    
    # 3. Cleanup
    print(f"3. Cleaning up raw 3D file {era5_3d_file} to save space...")
    # os.remove(era5_3d_file) # Uncomment for actual run

def run_batch():
    years = [2020, 2021, 2022, 2023, 2024]
    months = list(range(1, 13))
    
    print("STARTING 5-YEAR BATCH ORCHESTRATOR")
    
    for year in years:
        for month in months:
            # Check if this month is already completed
            # if check_completed(year, month): continue
            
            process_month(year, month)
            
            # For this dry run, break immediately
            break
        break
        
    print("Batch orchestrator dry-run complete.")

if __name__ == '__main__':
    run_batch()
