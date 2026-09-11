import unittest
from src.transport.trajectory_model import KinematicTrajectoryModel
from src.transport.source_receptor import calculate_ensemble_influence
import numpy as np

class TestTrajectoryConvergence(unittest.TestCase):
    
    def test_rk4_timestep_convergence(self):
        """
        Test 5: Halving the timestep should produce negligible trajectory difference.
        """
        # We will use the Delhi case for the 24h trajectory
        ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
        GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
        model = KinematicTrajectoryModel(ERA5_DATA)
        
        lat = 28.6139
        lon = 77.2090
        time = '2020-11-01 12:00:00'
        
        # dt = 1 hour (3600 sec)
        traj_1h = model.run_backward_trajectory(lat, lon, time, hours=24, dt_sec=3600)
        
        # dt = 30 min (1800 sec)
        traj_30m = model.run_backward_trajectory(lat, lon, time, hours=24, dt_sec=1800)
        
        # Compare endpoints
        end_lat_1h = traj_1h.iloc[-1]['latitude']
        end_lon_1h = traj_1h.iloc[-1]['longitude']
        
        end_lat_30m = traj_30m.iloc[-1]['latitude']
        end_lon_30m = traj_30m.iloc[-1]['longitude']
        
        # Difference in km
        lat_diff_km = abs(end_lat_1h - end_lat_30m) * 111.0
        lon_diff_km = abs(end_lon_1h - end_lon_30m) * 111.0 * np.cos(np.radians(end_lat_1h))
        sep_km = np.sqrt(lat_diff_km**2 + lon_diff_km**2)
        
        # calculate_ensemble_influence expects an 'ensemble_member_id' column
        traj_1h['ensemble_member_id'] = 0
        traj_30m['ensemble_member_id'] = 0
        
        inf_1h = calculate_ensemble_influence(traj_1h, GRID_FILE, 'IND_047_021')
        inf_30m = calculate_ensemble_influence(traj_30m, GRID_FILE, 'IND_047_021')
        
        set_1h = set(inf_1h['source_grid_id'].dropna().values)
        set_30m = set(inf_30m['source_grid_id'].dropna().values)
        
        overlap = set_1h.intersection(set_30m)
        agreement = len(overlap) / max(len(set_1h), len(set_30m), 1)
        
        print(f"\nTimestep 60m vs 30m Separation: {sep_km:.2f} km")
        print(f"Grid Classification Agreement: {agreement*100:.1f}%")
        
        self.assertTrue(agreement > 0.8, f"Agreement {agreement} too low")

if __name__ == '__main__':
    unittest.main()
