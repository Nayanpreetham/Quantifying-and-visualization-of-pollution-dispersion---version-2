import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from src.transport.trajectory_model import KinematicTrajectoryModel
from src.transport.source_receptor import calculate_trajectory_influence
from src.transport.transport_weighting import calculate_transport_weighted_contribution
import warnings
warnings.filterwarnings('ignore')

print("Running 10-City Regional Transport Experiment (LKT Model)...")

TIMESTAMP = '2020-11-01 12:00:00'
ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
AGG_GRID_FILE = 'data/processed/grid_aggregated/aggregated_50km_20201101_120000.csv'

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

grid = gpd.read_file(GRID_FILE)
traj_model = KinematicTrajectoryModel(ERA5_DATA)

report_lines = ["# 10 Cities Regional Transport Validation (Lagrangian Kinematic Trajectory)\n", f"Date: {TIMESTAMP} UTC\n"]

for city, gid in CITIES.items():
    print(f"\nProcessing {city} ({gid})...")
    report_lines.append(f"## {city} (Target: {gid})")
    
    # Get target coords
    target_row = grid[grid['grid_id'] == gid].iloc[0]
    lon, lat = target_row.geometry.centroid.x, target_row.geometry.centroid.y
    
    # Run 72-hour backward trajectory
    traj_df = traj_model.run_backward_trajectory(lat, lon, TIMESTAMP, hours=72, dt_sec=1800)
    
    os.makedirs('data/processed/trajectories', exist_ok=True)
    traj_file = f"data/processed/trajectories/traj_{gid}_72h.csv"
    traj_df.to_csv(traj_file, index=False)
    
    # Calculate source-receptor influence matrix (T_ij)
    influence_df = calculate_trajectory_influence(traj_df, GRID_FILE, gid)
    influence_file = f"data/processed/trajectories/influence_{gid}.csv"
    influence_df.to_csv(influence_file, index=False)
    
    if not influence_df.empty:
        pct_out = influence_df['pct_mass_outside_domain'].iloc[0]
        
        # Calculate transport-weighted contribution (C_ij)
        contrib_file = calculate_transport_weighted_contribution(
            gid, TIMESTAMP, influence_file, AGG_GRID_FILE, 'data/processed/contributions_regional'
        )
        
        contrib_df = pd.read_csv(contrib_file)
        top_sources = contrib_df[contrib_df['rank'] <= 5]
        
        report_lines.append(f"- **72-h Trajectory Tracking**: Complete.")
        report_lines.append(f"- **Transport Outside India Domain**: {pct_out:.1f}%")
        report_lines.append("- **Top 5 Regional Contributing Sources:**")
        
        for _, row in top_sources.iterrows():
            report_lines.append(f"  - **{row['source_grid_id']}** ({row['distance_km']:.1f} km upstream, AQI: {row['baseline_pollution_indicator']:.1f}): {row['contribution_percent']:.1f}%")
    else:
        report_lines.append("- No trajectory influence found within domain.")
        
    report_lines.append("\n")

with open('docs/10_cities_regional_transport.md', 'w') as f:
    f.write("\n".join(report_lines))

print("\nExperiment complete. Saved to docs/10_cities_regional_transport.md")
