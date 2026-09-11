import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from src.transport.trajectory_model import KinematicTrajectoryModel
from src.transport.source_receptor import calculate_trajectory_influence
from src.transport.transport_weighting import calculate_transport_weighted_contribution
import glob

print("Running Regional Transport Proof of Concept (LKT Model)...")

TIMESTAMP = '2020-11-01 12:00:00'
ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
AGG_GRID_FILE = 'data/processed/grid_aggregated/aggregated_50km_20201101_120000.csv' # Assuming previously generated

CITIES = {
    'Delhi': (28.6139, 77.2090),
    'Mumbai': (19.0760, 72.8777),
    'Varanasi': (25.3176, 82.9739)
}

grid = gpd.read_file(GRID_FILE)

# Init Trajectory Model
traj_model = KinematicTrajectoryModel(ERA5_DATA)

report_lines = ["# Regional Trajectory Transport Proof of Concept\n", f"Date: {TIMESTAMP} UTC\n"]

for city, coords in CITIES.items():
    pt = gpd.GeoSeries([Point(coords[1], coords[0])], crs='EPSG:4326')
    dist = grid.geometry.distance(pt[0])
    idx = dist.idxmin()
    gid = grid.iloc[idx]['grid_id']
    
    print(f"\nProcessing {city} ({gid})...")
    report_lines.append(f"## {city} (Target: {gid})")
    
    # Run 72-hour backward trajectory
    traj_df = traj_model.run_backward_trajectory(coords[0], coords[1], TIMESTAMP, hours=72, dt_sec=1800)
    
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

with open('docs/regional_transport_poc.md', 'w') as f:
    f.write("\n".join(report_lines))

print("\nExperiment complete. Saved to docs/regional_transport_poc.md")
