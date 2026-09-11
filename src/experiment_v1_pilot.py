import os
import pandas as pd
import geopandas as gpd
from src.transport.trajectory_model import KinematicTrajectoryModel
from src.transport.source_receptor import calculate_trajectory_influence
from src.transport.transport_weighting import calculate_transport_weighted_contribution
import warnings
warnings.filterwarnings('ignore')

TIMESTAMP = '2020-11-01 12:00:00'
ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
AGG_GRID_FILE = 'data/processed/grid_aggregated/aggregated_50km_20201101_120000.csv'

CITIES = {
    'Delhi': 'IND_047_021',
    'Mumbai': 'IND_026_012',
    'Varanasi': 'IND_040_032'
}

grid = gpd.read_file(GRID_FILE)
traj_model = KinematicTrajectoryModel(ERA5_DATA)

report = []
report.append("# Mode A: 2D Near-Surface Kinematic Trajectory Pilot")
report.append(f"Date: {TIMESTAMP} UTC\n")
report.append("This report executes the Python-native kinematic trajectory model using RK4 integration over ERA5 meteorological fields. **This is explicitly a 2D near-surface pilot.**\n")

for city, gid in CITIES.items():
    print(f"Processing {city}...")
    report.append(f"## {city}")
    report.append(f"![{city} Trajectory]({city}_trajectory.png)\n")
    
    target_row = grid[grid['grid_id'] == gid].iloc[0]
    lon, lat = target_row.geometry.centroid.x, target_row.geometry.centroid.y
    
    for hours in [24, 48, 72]:
        traj_df = traj_model.run_backward_trajectory(lat, lon, TIMESTAMP, hours=hours, dt_sec=3600)
        
        traj_file = f"data/processed/trajectories/traj_{gid}_{hours}h.csv"
        traj_df.to_csv(traj_file, index=False)
        
        influence_df = calculate_trajectory_influence(traj_df, GRID_FILE, gid)
        influence_file = f"data/processed/trajectories/influence_{gid}_{hours}h.csv"
        influence_df.to_csv(influence_file, index=False)
        
        if not influence_df.empty:
            pct_in = influence_df['pct_mass_inside_domain'].iloc[0]
            pct_out = influence_df['pct_mass_outside_domain'].iloc[0]
            
            contrib_file = calculate_transport_weighted_contribution(
                gid, TIMESTAMP, influence_file, AGG_GRID_FILE, 'data/processed/contributions_regional'
            )
            
            contrib_df = pd.read_csv(contrib_file)
            top_sources = contrib_df[contrib_df['rank'] <= 10]
            
            dist_max = traj_df.apply(lambda r: target_row.geometry.centroid.distance(gpd.points_from_xy([r['longitude']], [r['latitude']], crs='EPSG:4326')[0]) / 1000.0, axis=1).max()
            # Approx distance using pyproj or simple Euclidean for diagnostic
            dist_max = 111.0 * max(abs(traj_df['latitude'] - lat).max(), abs(traj_df['longitude'] - lon).max())
            
            report.append(f"### {hours}-hour Trajectory")
            report.append(f"- **Max Distance from Target**: ~{dist_max:.1f} km")
            report.append(f"- **Source Grids Crossed**: {len(influence_df)}")
            report.append(f"- **Domain**: {pct_in:.1f}% Indian residence, {pct_out:.1f}% Outside-domain")
            report.append("- **Top Sources:**")
            
            for _, row in top_sources.iterrows():
                report.append(f"  - **{row['source_grid_id']}**: {row['contribution_percent']:.1f}% (Distance: {row['distance_km']:.1f} km)")
        report.append("")

report.append("## Exact Data Requirements for Mode B (Regional 3D)")
report.append("To implement a true 3D regional atmospheric transport model, the following ERA5 fields on pressure levels are required:")
report.append("- u (u-component of wind) at 1000, 925, 850, 700 hPa")
report.append("-  (v-component of wind) at 1000, 925, 850, 700 hPa")
report.append("- omega (vertical velocity) at corresponding levels")
report.append("Integration would use 4D linear/spline interpolation (lat, lon, pressure, time).")

with open('docs/regional_transport_pilot_report.md', 'w') as f:
    f.write("\n".join(report))

print("Done.")
