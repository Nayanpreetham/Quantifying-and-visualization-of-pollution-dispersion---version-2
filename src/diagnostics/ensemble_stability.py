import pandas as pd
from src.transport.ensemble_model import EnsembleTrajectoryModel
from src.transport.source_receptor import calculate_ensemble_influence
import os
import warnings
warnings.filterwarnings('ignore')

TIMESTAMP = '2020-11-01 12:00:00'
ERA5_3D = 'data/raw/era5/era5_3d_2020_11_01.nc'
ERA5_SFC = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'

# Delhi
TARGET_LAT, TARGET_LON, TARGET_GID = 28.61, 77.21, 'IND_047_021'

def run_stability_check():
    model = EnsembleTrajectoryModel(ERA5_3D, ERA5_SFC)
    
    # We will slice the ensemble members. We know the engine currently generates 20.
    # To test N=5, 10, 20 we slice the dataframe.
    full_ensemble = model.run_ensemble(TARGET_LAT, TARGET_LON, TIMESTAMP, hours=72)
    
    if full_ensemble.empty:
        print("No ensemble traces generated.")
        return
        
    ns = [5, 10, 20]
    results = {}
    
    for n in ns:
        # filter to first N members
        subset = full_ensemble[full_ensemble['ensemble_member_id'] < n]
        inf = calculate_ensemble_influence(subset, GRID_FILE, TARGET_GID)
        if not inf.empty:
            inf = inf.sort_values('transport_weight', ascending=False)
            results[n] = inf['source_grid_id'].values.tolist()
            
    report = ["# Ensemble Source Ranking Stability", ""]
    
    for i in range(len(ns)-1):
        n1 = ns[i]
        n2 = ns[i+1]
        
        r1 = results.get(n1, [])
        r2 = results.get(n2, [])
        
        top1_stable = (r1[:1] == r2[:1])
        top3_overlap = len(set(r1[:3]).intersection(set(r2[:3]))) / 3.0 * 100
        top5_overlap = len(set(r1[:5]).intersection(set(r2[:5]))) / 5.0 * 100
        
        report.append(f"### {n1} vs {n2} trajectories")
        report.append(f"- **Top-1 Stability**: {top1_stable}")
        report.append(f"- **Top-3 Overlap**: {top3_overlap:.1f}%")
        report.append(f"- **Top-5 Overlap**: {top5_overlap:.1f}%")
        report.append("")
        
    os.makedirs('docs', exist_ok=True)
    with open('docs/ensemble_stability.md', 'w') as f:
        f.write("\\n".join(report))
        
    print("Stability report generated at docs/ensemble_stability.md")

if __name__ == '__main__':
    run_stability_check()
