import os
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from src.transport.ensemble_model import EnsembleTrajectoryModel
from src.transport.source_receptor import calculate_ensemble_influence

CITIES = {
    'Delhi': (28.61, 77.21, 'IND_047_021'),
    'Lucknow': (26.84, 80.94, 'IND_043_028'),
    'Varanasi': (25.32, 82.97, 'IND_040_032'),
    'Kanpur': (26.44, 80.33, 'IND_042_027'),
    'Patna': (25.59, 85.13, 'IND_041_037'),
    'Kolkata': (22.57, 88.36, 'IND_034_043'),
    'Mumbai': (19.07, 72.87, 'IND_026_012'),
    'Ahmedabad': (23.02, 72.57, 'IND_035_011'),
    'Hyderabad': (17.38, 78.48, 'IND_022_023'),
    'Bengaluru': (12.97, 77.59, 'IND_012_021')
}

DATES = [
    '2020-10-31 00:00:00',
    '2020-10-31 12:00:00',
    '2020-11-01 00:00:00',
    '2020-11-01 12:00:00',
    # Ideally 7 days, using 4 distinct timesteps in our available downloaded window
]

ERA5_3D = 'data/raw/era5/era5_3d_2020_11_01.nc'
ERA5_SFC = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'

def run_pilot():
    model = EnsembleTrajectoryModel(ERA5_3D, ERA5_SFC)
    
    report = ["# 10-City Multi-Day Validation Pilot", ""]
    
    for city, (lat, lon, gid) in CITIES.items():
        print(f"Processing {city}...")
        report.append(f"## {city} (Grid: {gid})")
        
        for ts in DATES:
            # We run the ensemble which generates 20 trajectories (5 spatial x 4 vertical)
            ensemble_df = model.run_ensemble(lat, lon, ts, hours=72)
            if ensemble_df.empty:
                continue
                
            inf_df = calculate_ensemble_influence(ensemble_df, GRID_FILE, gid)
            
            if inf_df.empty:
                continue
                
            inf_df = inf_df.sort_values('transport_weight', ascending=False)
            top5 = inf_df.head(5)
            
            # Extract outside fractions
            frac_ocean = inf_df['frac_Ocean'].iloc[0] if 'frac_Ocean' in inf_df.columns else 0
            frac_pak = inf_df['frac_Pakistan'].iloc[0] if 'frac_Pakistan' in inf_df.columns else 0
            frac_out = inf_df['frac_outside_domain'].iloc[0]
            
            report.append(f"### {ts}")
            report.append(f"- **Total Ensemble Traces**: {len(ensemble_df['ensemble_member_id'].unique())}")
            report.append(f"- **Top 5 Source Grids**: {', '.join(top5['source_grid_id'].values)}")
            report.append(f"- **Domain Breakdown**: Ocean: {frac_ocean:.1f}% | Pakistan: {frac_pak:.1f}% | Outside 50km Grid: {frac_out:.1f}%")
            
        report.append("")
        
    os.makedirs('docs', exist_ok=True)
    with open('docs/validation_pilot_results.md', 'w') as f:
        f.write("\\n".join(report))
        
    print("Pilot completed. Results in docs/validation_pilot_results.md")

if __name__ == '__main__':
    run_pilot()
