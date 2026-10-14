"""
Core 50 km Full-Grid Transport Adapter & Dispersion Engine
Phase 19 — National 50 km Grid-to-Grid Pollution Transport

Integrates the 50 km x 50 km national grid (EPSG:7755) with the verified 2D
Lagrangian ensemble advection physics. Preserves unconditional time-aggregation,
exact probability closure (sum T == 1.0), and explicit OUTSIDE_DOMAIN boundary accounting.
"""

import os
import pyproj
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

# Grid Constants from Phase 18
PROJ_CRS = "EPSG:7755"
X_ORIGIN_M = 2800000.0
Y_ORIGIN_M = 2200000.0
GRID_STEP_M = 50000.0
N_COLS = 58
N_ROWS = 62
WINDOWS = [1.0, 3.0, 6.0, 12.0, 24.0]
N_ENSEMBLE = 10
EARTH_RADIUS_KM = 6371.0


class National50kmTransportAdapter:
    def __init__(self, grid_csv_path="results/phase18_grid_audit/india_50km_grid.csv"):
        if not os.path.exists(grid_csv_path):
            raise FileNotFoundError(f"50 km grid file not found at: {grid_csv_path}")
            
        self.grid_df = pd.read_csv(grid_csv_path)
        self.n_cells = len(self.grid_df)
        self.valid_cell_ids = set(self.grid_df['grid_id_50km'].values)
        
        # Array lookups
        self.cell_ids = self.grid_df['grid_id_50km'].values
        self.src_lats = self.grid_df['center_latitude_deg'].values
        self.src_lons = self.grid_df['center_longitude_deg'].values
        self.src_x = self.grid_df['x_center_m'].values
        self.src_y = self.grid_df['y_center_m'].values
        self.land_fractions = self.grid_df['land_fraction'].values
        
        # Fast dictionary for destination coordinates
        self.coords_lookup = dict(zip(
            self.cell_ids,
            zip(self.src_lats, self.src_lons)
        ))
        
        # Fast coordinate transformer (WGS84 -> EPSG:7755)
        self.transformer = pyproj.Transformer.from_crs("EPSG:4326", PROJ_CRS, always_xy=True)

    def map_points_to_grid(self, p_lons_flat, p_lats_flat):
        """
        Maps an array of (lon, lat) points in WGS84 to 50 km grid IDs in O(1).
        Returns an array of grid ID strings ('IND_50KM_rXXX_cYYY' or 'OUTSIDE_DOMAIN').
        """
        xs, ys = self.transformer.transform(p_lons_flat, p_lats_flat)
        cols = np.floor((xs - X_ORIGIN_M) / GRID_STEP_M).astype(int)
        rows = np.floor((ys - Y_ORIGIN_M) / GRID_STEP_M).astype(int)
        
        dest_ids = []
        for r, c in zip(rows, cols):
            if 0 <= r < N_ROWS and 0 <= c < N_COLS:
                gid = f"IND_50KM_r{r:03d}_c{c:03d}"
                if gid in self.valid_cell_ids:
                    dest_ids.append(gid)
                else:
                    dest_ids.append("OUTSIDE_DOMAIN")
            else:
                dest_ids.append("OUTSIDE_DOMAIN")
                
        return np.array(dest_ids, dtype=object)

    def simulate_synoptic_step(self, u_interp_func, v_interp_func, synoptic_step_idx, timestamp_str):
        """
        Executes 2D Lagrangian ensemble advection for all 1,380 source cells
        across all 5 advection horizons (1h, 3h, 6h, 12h, 24h).
        
        Returns:
        - step_targets_list: list of dicts with (source, dest, window, count, fraction)
        """
        pts = np.vstack([self.src_lats, self.src_lons]).T
        u_src = u_interp_func(pts)
        v_src = v_interp_func(pts)
        
        base_spd = np.hypot(u_src, v_src)
        base_ang = np.arctan2(v_src, u_src)
        
        # Coherent Gaussian ensemble velocity perturbations (N=10) per synoptic release
        rng = np.random.RandomState(42 + synoptic_step_idx)
        spd_pert = np.maximum(0.2, base_spd[:, None] + rng.normal(0, 0.4, size=(self.n_cells, N_ENSEMBLE)))
        spd_pert[:, 0] = base_spd  # Central member is deterministic
        
        ang_pert = base_ang[:, None] + rng.normal(0, np.radians(12.0), size=(self.n_cells, N_ENSEMBLE))
        ang_pert[:, 0] = base_ang  # Central member is deterministic
        
        u_p = spd_pert * np.cos(ang_pert)
        v_p = spd_pert * np.sin(ang_pert)
        
        # Track persistent boundary exit across increasing window horizons
        has_exited_domain = np.zeros((self.n_cells, N_ENSEMBLE), dtype=bool)
        
        step_results = []
        
        for w_idx, w in enumerate(WINDOWS):
            dt_sec = w * 3600.0
            
            dx_m = u_p * dt_sec
            dy_m = v_p * dt_sec
            
            dlat = dy_m / 111000.0
            dlon = dx_m / (111000.0 * np.cos(np.radians(self.src_lats[:, None])))
            
            p_lats = self.src_lats[:, None] + dlat
            p_lons = self.src_lons[:, None] + dlon
            
            # Map all 1,380 x 10 particles
            dest_ids_flat = self.map_points_to_grid(p_lons.ravel(), p_lats.ravel())
            dest_matrix = dest_ids_flat.reshape(self.n_cells, N_ENSEMBLE)
            
            # Enforce boundary persistence: once a particle exits terrestrial India, it remains OUTSIDE_DOMAIN
            dest_matrix[has_exited_domain] = "OUTSIDE_DOMAIN"
            has_exited_domain |= (dest_matrix == "OUTSIDE_DOMAIN")
            
            # Bin into destination counts per source
            for src_idx in range(self.n_cells):
                src_gid = self.cell_ids[src_idx]
                row_dests = dest_matrix[src_idx, :]
                unique_d, counts = np.unique(row_dests, return_counts=True)
                
                for d_gid, cnt in zip(unique_d, counts):
                    frac = cnt / float(N_ENSEMBLE)
                    step_results.append((src_gid, d_gid, w, cnt, frac))
                    
        return step_results


def calculate_haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculates Haversine distance in km between two lat/lon points."""
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(EARTH_RADIUS_KM * c)
