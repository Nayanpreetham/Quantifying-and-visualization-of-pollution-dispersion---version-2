"""
10-City Multi-Day Validation Pilot
=====================================
Executes the 10-city source-influence pilot using:
  - 3D RK4 ensemble backward trajectories
  - Fast KD-tree grid lookup (instead of slow sjoin)
  - Periodic disturbance representation
  - Source-category weighting (TRANSPORT_ONLY mode until emissions are loaded)
  - City-level daily AQI for correlation check

Cities chosen to cover different Indian pollution regimes:
  Delhi      - Indo-Gangetic Plain, severe winter pollution
  Lucknow    - IGP, downwind of Delhi/Kanpur corridor
  Varanasi   - Eastern IGP, crop burning influence
  Kanpur     - Industrial IGP city
  Patna      - Eastern IGP, Bihar
  Kolkata    - Eastern India, Bay of Bengal proximity
  Mumbai     - Western coastal, Arabian Sea boundary
  Ahmedabad  - Northwest, Rajasthan dust influence
  Hyderabad  - Deccan Plateau, different meteorological regime
  Bengaluru  - Southern India, lower pollution burden

Run with available 2020-11-01 ERA5 data (pilot window).
"""

import os
import time
import warnings
import pandas as pd
import numpy as np
warnings.filterwarnings('ignore')

from src.transport.ensemble_model import EnsembleTrajectoryModel
from src.transport.grid_lookup import GridRasterIndex, fast_ensemble_influence
from src.physics.periodic_disturbance import compute_periodic_disturbance, compute_event_perturbation
from src.physics.source_categories import SourceCategoryWeighter, compute_source_influence_report

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
ERA5_3D  = 'data/raw/era5/era5_3d_2020_11_01.nc'
ERA5_SFC = 'data/processed/era5/era5_2020_11.nc'
GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
EMISSIONS_FILE = None  # Set path when emissions data are available

# Timestamps within the available ERA5 pilot window
PILOT_TIMESTAMPS = [
    '2020-11-01 00:00:00',
    '2020-11-01 12:00:00',
]

CITIES = {
    'Delhi':     (28.61, 77.21, 'IND_047_021'),
    'Lucknow':   (26.84, 80.94, 'IND_043_028'),
    'Varanasi':  (25.32, 82.97, 'IND_040_032'),
    'Kanpur':    (26.44, 80.33, 'IND_042_027'),
    'Patna':     (25.59, 85.13, 'IND_041_037'),
    'Kolkata':   (22.57, 88.36, 'IND_034_043'),
    'Mumbai':    (19.07, 72.87, 'IND_026_012'),
    'Ahmedabad': (23.02, 72.57, 'IND_035_011'),
    'Hyderabad': (17.38, 78.48, 'IND_022_023'),
    'Bengaluru': (12.97, 77.59, 'IND_012_021'),
}

TRAJECTORY_HOURS = 72
ENSEMBLE_DT_SEC  = 1800  # 30-min timestep


def load_observed_aqi(city_name: str) -> pd.DataFrame:
    """Load city-level daily AQI from CPCB bulletin data."""
    aqi_path = f'data/raw/cpcb/aqi_data/{city_name}_AQIBulletins.csv'
    if not os.path.exists(aqi_path):
        return pd.DataFrame()
    df = pd.read_csv(aqi_path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['date', 'Index Value'])
    df = df.rename(columns={'Index Value': 'aqi'})
    return df[['date', 'aqi']].sort_values('date')


def run_pilot():
    if not os.path.exists(ERA5_3D):
        print(f"ERROR: 3D ERA5 file not found: {ERA5_3D}")
        print("Please ensure era5_3d_2020_11_01.nc is downloaded via src/data/download_era5_pressure_levels.py")
        return

    if not os.path.exists(ERA5_SFC):
        print(f"ERROR: Surface ERA5 file not found: {ERA5_SFC}")
        return

    print("=" * 65)
    print("10-CITY SOURCE INFLUENCE PILOT (TRANSPORT_ONLY MODE)")
    print("=" * 65)
    print(f"ERA5 3D:  {ERA5_3D}")
    print(f"ERA5 SFC: {ERA5_SFC}")
    print()

    # Build model objects once
    t0 = time.time()
    print("Loading ensemble trajectory model...")
    model = EnsembleTrajectoryModel(ERA5_3D, ERA5_SFC)
    print(f"  done ({time.time()-t0:.1f}s)")

    t0 = time.time()
    print("Building fast grid index...")
    grid_index = GridRasterIndex(GRID_FILE)
    print(f"  done ({time.time()-t0:.1f}s), {len(grid_index.grid_ids)} cells")

    weighter = SourceCategoryWeighter(EMISSIONS_FILE)

    os.makedirs('docs', exist_ok=True)
    results = []

    for city, (lat, lon, gid) in CITIES.items():
        print(f"\n--- {city} ({gid}) ---")

        # Load observed AQI for this city
        obs_df = load_observed_aqi(city)
        obs_nov1 = obs_df[obs_df['date'] == '2020-11-01']['aqi'].values
        obs_aqi = float(obs_nov1[0]) if len(obs_nov1) > 0 else float('nan')
        print(f"  Observed AQI 2020-11-01: {obs_aqi}")

        for ts_str in PILOT_TIMESTAMPS:
            ts = pd.Timestamp(ts_str)
            print(f"  Timestamp: {ts_str}")

            t_traj = time.time()
            ensemble_df = model.run_ensemble(lat, lon, ts_str, hours=TRAJECTORY_HOURS, dt_sec=ENSEMBLE_DT_SEC)
            traj_time = time.time() - t_traj
            print(f"    Trajectories: {ensemble_df['ensemble_member_id'].nunique()} members, {len(ensemble_df)} points ({traj_time:.1f}s)")

            if ensemble_df.empty:
                print("    No trajectories produced. Skipping.")
                continue

            # Fast grid lookup
            t_grid = time.time()
            influence_df = fast_ensemble_influence(ensemble_df, grid_index, gid)
            grid_time = time.time() - t_grid
            print(f"    Grid assignment: {len(influence_df)} source cells ({grid_time:.2f}s)")

            if influence_df.empty:
                print("    No source cells found.")
                continue

            # Periodic disturbance
            event_amp = compute_event_perturbation(ts)
            D = compute_periodic_disturbance(ts, event_perturbation=event_amp)
            print(f"    Disturbance factor D(t) = {D:.4f}  (event_amp={event_amp})")

            # Source-category weighting
            report = compute_source_influence_report(
                gid, ts, influence_df, weighter, disturbance_factor=D
            )

            # Extract top-5 sources
            top5 = report.get('top5_sources', [])
            print(f"    Top-5 source cells:")
            for i, s in enumerate(top5, 1):
                print(f"      {i}. {s['source_grid_id']}  transport_weight={s['transport_weight']:.4f}")

            # Domain fractions
            domain = report.get('domain_fractions', {})
            frac_outside = influence_df['frac_outside_domain'].iloc[0] if 'frac_outside_domain' in influence_df.columns else float('nan')
            frac_ocean   = domain.get('frac_Ocean', 0.0)
            frac_pakistan = domain.get('frac_Pakistan', 0.0)
            frac_bang    = domain.get('frac_Bangladesh', 0.0)
            print(f"    Domain: outside_50km_grid={frac_outside:.1f}%  Ocean={frac_ocean:.1f}%  Pakistan={frac_pakistan:.1f}%  Bangladesh={frac_bang:.1f}%")

            results.append({
                'city': city,
                'grid_id': gid,
                'timestamp': ts_str,
                'obs_aqi': obs_aqi,
                'n_ensemble_members': ensemble_df['ensemble_member_id'].nunique(),
                'n_source_cells': report.get('n_source_cells', 0),
                'disturbance_factor': D,
                'mode': report.get('mode'),
                'top1_grid': top5[0]['source_grid_id'] if top5 else None,
                'top1_weight': top5[0]['transport_weight'] if top5 else None,
                'frac_outside_domain': frac_outside,
                'frac_Ocean': frac_ocean,
                'frac_Pakistan': frac_pakistan,
                'frac_Bangladesh': frac_bang,
                'traj_time_s': traj_time,
                'grid_time_s': grid_time,
            })

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv('docs/pilot_results_10city.csv', index=False)
    print("\n" + "=" * 65)
    print("PILOT COMPLETE")
    print(f"Results saved to docs/pilot_results_10city.csv")
    print()
    print(results_df[['city', 'timestamp', 'obs_aqi', 'n_ensemble_members', 'disturbance_factor',
                       'top1_grid', 'frac_outside_domain']].to_string(index=False))
    print()
    print("NOTE: Mode =", results_df['mode'].iloc[0] if not results_df.empty else 'N/A')
    print("Output represents TRANSPORT-ONLY source influence, not emission-weighted contribution.")


if __name__ == '__main__':
    run_pilot()
