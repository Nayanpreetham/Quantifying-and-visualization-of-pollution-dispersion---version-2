import numpy as np
import pandas as pd
from src.transport.trajectory_model_3d import KinematicTrajectoryModel3D
from src.physics.atmosphere import pressure_to_altitude_isa, altitude_to_pressure_isa

class EnsembleTrajectoryModel:
    def __init__(self, era5_3d_file, era5_sfc_file):
        self.traj_model = KinematicTrajectoryModel3D(era5_3d_file, era5_sfc_file)
        
    def _get_surface_pressure(self, lat, lon, time_str):
        try:
            sp = self.traj_model.interp_sp((pd.to_datetime(time_str).timestamp(), lat, lon))
            return float(sp) / 100.0
        except Exception:
            return 1013.25

    def _agl_to_pressure(self, height_agl_m, sp_hpa):
        """
        Convert height AGL to pressure (hPa) using ISA.
        
        Strategy: compute ISA altitude of surface (from sp_hpa), add height_agl_m
        to get ASL altitude, then convert back to pressure.
        
        This is more physically defensible than the hardcoded sp - h/8 approximation.
        sp_hpa is used as an anchor for terrain elevation.
        """
        surface_asl_m = pressure_to_altitude_isa(sp_hpa)
        target_asl_m = surface_asl_m + height_agl_m
        pressure_hpa = altitude_to_pressure_isa(target_asl_m)
        return pressure_hpa
            
    def run_ensemble(self, target_lat, target_lon, time_start, hours=72, dt_sec=1800):
        # 1. Spatial Perturbations (approx 10 km)
        dlat = 10.0 / 111.32
        dlon = 10.0 / (111.32 * np.cos(np.radians(target_lat)))
        
        spatial_offsets = [
            (0, 0),             # Center
            (dlat, 0),          # North
            (-dlat, 0),         # South
            (0, dlon),          # East
            (0, -dlon)          # West
        ]
        
        # 2. Vertical Perturbations (AGL)
        vertical_agl = [50, 100, 300, 500]
        
        ensemble_results = []
        traj_id = 0
        
        for d_lat, d_lon in spatial_offsets:
            lat = target_lat + d_lat
            lon = target_lon + d_lon
            
            sp_hpa = self._get_surface_pressure(lat, lon, time_start)
            
            for h_agl in vertical_agl:
                # ISA-based AGL to pressure conversion
                p_start = self._agl_to_pressure(h_agl, sp_hpa)
                
                if p_start < 500:
                    continue
                    
                traj_df = self.traj_model.run_backward_trajectory_3d(
                    lat, lon, p_start, time_start, hours=hours, dt_sec=dt_sec
                )
                
                if not traj_df.empty:
                    traj_df['ensemble_member_id'] = traj_id
                    traj_df['release_lat'] = lat
                    traj_df['release_lon'] = lon
                    traj_df['release_agl'] = h_agl
                    ensemble_results.append(traj_df)
                    
                traj_id += 1
                
        if ensemble_results:
            return pd.concat(ensemble_results, ignore_index=True)
        return pd.DataFrame()
