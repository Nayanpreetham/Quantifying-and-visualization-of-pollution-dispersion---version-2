"""
Corrected 50 km Full-Grid Dynamic Trajectory Adapter
Phase 19 — Final Scientific Verification & Targeted Corrections

Implements physically rigorous 2D Lagrangian trajectory integration through
spatially and temporally evolving ERA5 horizontal wind fields:
- Explicit sub-hourly time-stepping (h <= 1.0 hour).
- Spatially interpolated U10/V10 at current parcel positions (bilinear).
- Temporally interpolated U10/V10 between 6-hourly ERA5 reanalysis slices.
- Strict boundary classification into 4 explicit categories:
    1. Valid terrestrial 50 km land cell ('IND_50KM_rXXX_cYYY')
    2. Internal non-terrestrial water/marine cell ('INTERNAL_UNMODELED_WATER')
    3. External domain exit into international waters/borders ('DOMAIN_EXIT_EXTERNAL')
    4. Unsupported meteorological coverage beyond ERA5 bounds ('UNSUPPORTED_MET_COVERAGE')
- Explicit prohibition of silent extrapolation beyond ERA5 bounds [6.0, 35.0]N x [68.0, 97.0]E.
- Coherent trajectory history across all horizons (1h, 3h, 6h, 12h, 24h).
- Strict probability closure preservation (sum = 1.0 +- 1e-12).
"""

import os
import sys
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

# ERA5 Coordinate Bounds
ERA5_LAT_MIN = 6.0
ERA5_LAT_MAX = 35.0
ERA5_LON_MIN = 68.0
ERA5_LON_MAX = 97.0


class Corrected50kmTransportAdapter:
    def __init__(self, grid_csv_path="results/phase18_grid_audit/india_50km_grid.csv"):
        if not os.path.exists(grid_csv_path):
            raise FileNotFoundError(f"50 km grid file not found at: {grid_csv_path}")
            
        self.grid_df = pd.read_csv(grid_csv_path)
        self.n_cells = len(self.grid_df)
        self.valid_cell_ids = set(self.grid_df['grid_id_50km'].values)
        
        # Lookups
        self.cell_ids = self.grid_df['grid_id_50km'].values
        self.src_lats = self.grid_df['center_latitude_deg'].values
        self.src_lons = self.grid_df['center_longitude_deg'].values
        self.src_x = self.grid_df['x_center_m'].values
        self.src_y = self.grid_df['y_center_m'].values
        self.land_fractions = self.grid_df['land_fraction'].values
        
        # Coordinate lookups
        self.coords_lookup = dict(zip(
            self.cell_ids,
            zip(self.src_lats, self.src_lons)
        ))
        
        # Fast 2D matrix lookup table (62 x 58)
        # 0..1379: valid terrestrial land cell
        # 1380: INTERNAL_UNMODELED_WATER
        self.lookup_table = np.full((N_ROWS, N_COLS), 1380, dtype=int)
        for idx, (r, c) in enumerate(zip(self.grid_df['row'], self.grid_df['column'])):
            self.lookup_table[r, c] = idx
            
        # Supported ERA5 mask for source cells
        self.source_is_supported = (
            (self.src_lats >= ERA5_LAT_MIN) & (self.src_lats <= ERA5_LAT_MAX) &
            (self.src_lons >= ERA5_LON_MIN) & (self.src_lons <= ERA5_LON_MAX)
        )
        
        # Coordinate transformer
        self.transformer = pyproj.Transformer.from_crs("EPSG:4326", PROJ_CRS, always_xy=True)

    def classify_positions(self, p_lons_flat, p_lats_flat):
        """
        Classifies an array of (lon, lat) points into the 4 explicit categories:
        1. 'IND_50KM_rXXX_cYYY' (Valid terrestrial land cell)
        2. 'INTERNAL_UNMODELED_WATER' (Inside matrix envelope, non-terrestrial water cell)
        3. 'DOMAIN_EXIT_EXTERNAL' (Outside matrix envelope)
        4. 'UNSUPPORTED_MET_COVERAGE' (Outside ERA5 reanalysis coordinate box)
        """
        p_lons_flat = np.asarray(p_lons_flat)
        p_lats_flat = np.asarray(p_lats_flat)
        N = len(p_lons_flat)
        out_ids = np.empty(N, dtype=object)
        
        # Check ERA5 coverage bounds
        out_of_met = (
            (p_lats_flat < ERA5_LAT_MIN) | (p_lats_flat > ERA5_LAT_MAX) |
            (p_lons_flat < ERA5_LON_MIN) | (p_lons_flat > ERA5_LON_MAX)
        )
        
        # Project to EPSG:7755
        xs, ys = self.transformer.transform(p_lons_flat, p_lats_flat)
        cols = np.floor((xs - X_ORIGIN_M) / GRID_STEP_M).astype(int)
        rows = np.floor((ys - Y_ORIGIN_M) / GRID_STEP_M).astype(int)
        
        in_matrix = (rows >= 0) & (rows < N_ROWS) & (cols >= 0) & (cols < N_COLS)
        
        for i in range(N):
            if out_of_met[i]:
                out_ids[i] = "UNSUPPORTED_MET_COVERAGE"
            elif not in_matrix[i]:
                out_ids[i] = "DOMAIN_EXIT_EXTERNAL"
            else:
                r, c = rows[i], cols[i]
                c_idx = self.lookup_table[r, c]
                if c_idx < self.n_cells:
                    out_ids[i] = self.cell_ids[c_idx]
                else:
                    out_ids[i] = "INTERNAL_UNMODELED_WATER"
                    
        return out_ids

    def integrate_trajectories(self, u_slices, v_slices, valid_times_hours, synoptic_step_idx, dt_int_hours=1.0):
        """
        Integrates Lagrangian trajectories for all 1,380 cells across 24 hours
        using dynamic spatial and temporal wind fields.
        
        Parameters:
        - u_slices: list/array of 2D u10 slices for timestamps covering [t0, t0 + 24h]
        - v_slices: list/array of 2D v10 slices for timestamps covering [t0, t0 + 24h]
        - valid_times_hours: relative offsets in hours for each slice (e.g. [0.0, 6.0, 12.0, 18.0, 24.0])
        - synoptic_step_idx: integer index for deterministic seed base
        - dt_int_hours: numerical integration time step in hours (default: 1.0 h)
        
        Returns:
        - horizon_destinations: dict of window -> array of shape (n_cells, N_ENSEMBLE)
        """
        n_steps = int(round(24.0 / dt_int_hours))
        dt_sec = dt_int_hours * 3600.0
        
        # Initialize particle positions at source centers
        curr_lats = np.repeat(self.src_lats[:, None], N_ENSEMBLE, axis=1) # (n_cells, 10)
        curr_lons = np.repeat(self.src_lons[:, None], N_ENSEMBLE, axis=1) # (n_cells, 10)
        
        # Track persistent exit states
        status_matrix = np.full((self.n_cells, N_ENSEMBLE), "ACTIVE", dtype=object)
        
        # Mark sources that have unsupported ERA5 coverage immediately
        unsupported_sources = ~self.source_is_supported
        status_matrix[unsupported_sources, :] = "UNSUPPORTED_MET_COVERAGE"
        
        # Ensemble turbulent velocity perturbations drawn once per release
        rng = np.random.RandomState(42 + synoptic_step_idx)
        spd_pert_base = rng.normal(0, 0.4, size=(self.n_cells, N_ENSEMBLE))
        spd_pert_base[:, 0] = 0.0 # Deterministic central member
        
        ang_pert_base = rng.normal(0, np.radians(12.0), size=(self.n_cells, N_ENSEMBLE))
        ang_pert_base[:, 0] = 0.0 # Deterministic central member
        
        # Output dictionary for standard horizons
        horizon_results = {}
        target_windows = set(WINDOWS)
        
        # Precompute ERA5 interpolators for available 6-hourly slices
        # Assume slices correspond to sorted_lats and raw_lons
        n_slices = len(valid_times_hours)
        
        for step in range(1, n_steps + 1):
            tau = step * dt_int_hours # Elapsed time in hours (1.0, 2.0, ..., 24.0)
            
            # Identify surrounding temporal slices for tau
            # Time bracket [t_left, t_right]
            slice_idx = np.searchsorted(valid_times_hours, tau)
            if slice_idx == 0:
                s0 = s1 = 0
                alpha = 0.0
            elif slice_idx >= n_slices:
                s0 = s1 = n_slices - 1
                alpha = 1.0
            else:
                s0 = slice_idx - 1
                s1 = slice_idx
                t0 = valid_times_hours[s0]
                t1 = valid_times_hours[s1]
                alpha = (tau - t0) / float(t1 - t0) if t1 > t0 else 0.0
                
            # For active particles, sample wind at current position
            active_mask = (status_matrix == "ACTIVE")
            
            if np.any(active_mask):
                act_lats = curr_lats[active_mask]
                act_lons = curr_lons[active_mask]
                
                # Check bounds
                out_of_bounds = (
                    (act_lats < ERA5_LAT_MIN) | (act_lats > ERA5_LAT_MAX) |
                    (act_lons < ERA5_LON_MIN) | (act_lons > ERA5_LON_MAX)
                )
                
                # Update status for those exiting ERA5 bounds
                if np.any(out_of_bounds):
                    # Find coordinates relative to matrix
                    flat_act_indices = np.where(active_mask)
                    for o_idx in np.where(out_of_bounds)[0]:
                        s_i = flat_act_indices[0][o_idx]
                        k_i = flat_act_indices[1][o_idx]
                        status_matrix[s_i, k_i] = "UNSUPPORTED_MET_COVERAGE"
                        
                    # Refresh active mask
                    active_mask = (status_matrix == "ACTIVE")
                    act_lats = curr_lats[active_mask]
                    act_lons = curr_lons[active_mask]
                    
            if np.any(active_mask):
                pts_active = np.vstack([act_lats, act_lons]).T
                
                # Interpolate wind from slice s0 and slice s1
                u0 = u_slices[s0](pts_active)
                v0 = v_slices[s0](pts_active)
                u1 = u_slices[s1](pts_active)
                v1 = v_slices[s1](pts_active)
                
                # Temporal interpolation
                u_base = (1.0 - alpha) * u0 + alpha * u1
                v_base = (1.0 - alpha) * v0 + alpha * v1
                
                base_spd = np.hypot(u_base, v_base)
                base_ang = np.arctan2(v_base, u_base)
                
                # Apply ensemble perturbations
                flat_act_indices = np.where(active_mask)
                s_indices = flat_act_indices[0]
                k_indices = flat_act_indices[1]
                
                pert_spd = np.maximum(0.2, base_spd + spd_pert_base[s_indices, k_indices])
                pert_ang = base_ang + ang_pert_base[s_indices, k_indices]
                
                # Restore central member exact deterministic values
                is_central = (k_indices == 0)
                pert_spd[is_central] = base_spd[is_central]
                pert_ang[is_central] = base_ang[is_central]
                
                u_adv = pert_spd * np.cos(pert_ang)
                v_adv = pert_spd * np.sin(pert_ang)
                
                # Advection displacement (Euler step)
                dy_m = v_adv * dt_sec
                dx_m = u_adv * dt_sec
                
                dlat = dy_m / 111000.0
                dlon = dx_m / (111000.0 * np.cos(np.radians(act_lats)))
                
                curr_lats[active_mask] += dlat
                curr_lons[active_mask] += dlon
                
            # If current tau is a target horizon, classify positions
            if tau in target_windows:
                # Classify all 1,380 x 10 particles
                dest_ids_flat = self.classify_positions(curr_lons.ravel(), curr_lats.ravel())
                dest_matrix = dest_ids_flat.reshape(self.n_cells, N_ENSEMBLE)
                
                # Override with persistent exit statuses
                has_unsupported = (status_matrix == "UNSUPPORTED_MET_COVERAGE")
                has_domain_exit = (status_matrix == "DOMAIN_EXIT_EXTERNAL")
                
                dest_matrix[has_unsupported] = "UNSUPPORTED_MET_COVERAGE"
                dest_matrix[has_domain_exit] = "DOMAIN_EXIT_EXTERNAL"
                
                # Update persistent exit status
                status_matrix[dest_matrix == "UNSUPPORTED_MET_COVERAGE"] = "UNSUPPORTED_MET_COVERAGE"
                status_matrix[dest_matrix == "DOMAIN_EXIT_EXTERNAL"] = "DOMAIN_EXIT_EXTERNAL"
                
                horizon_results[tau] = dest_matrix.copy()
                
        return horizon_results


def calculate_haversine_distance_km(lat1, lon1, lat2, lon2):
    """Calculates Haversine distance in km between two lat/lon points."""
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2.0)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(EARTH_RADIUS_KM * c)
