"""
Task B Corrected: Benchmark Pilot with Dynamic Trajectory Integration (Year 2021)
Phase 19 — Final Scientific Verification & Targeted Corrections

Executes the corrected 2D dynamic Lagrangian dispersion engine on the
representative 2021 benchmark pilot (28 synoptic steps, 2021-09-15 to 2021-09-21):
- Dynamic sub-hourly time-stepping (h = 1.0 h) through temporally and spatially evolving ERA5 winds.
- Strict 4-category boundary classification (Valid Land, Internal Water, Domain Exit, Unsupported Met).
- Zero silent extrapolation.
- Compares corrected outputs directly against previous frozen-wind pilot.
- Generates:
  * results/phase19_transport/correction_audit/pilot/transport_matrix_pilot_corrected_50km.csv
  * results/phase19_transport/correction_audit/comparison_old_vs_corrected.csv
  * results/phase19_transport/correction_audit/pilot/pilot_corrected_profile.csv
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import netCDF4 as nc
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from src.phase19.corrected_transport_adapter_50km import (
    Corrected50kmTransportAdapter,
    WINDOWS,
    N_ENSEMBLE,
    calculate_haversine_distance_km
)

def main():
    print("=== Phase 19 Task B Corrected: Dynamic Pilot Execution (Year 2021) ===")
    
    out_dir = "results/phase19_transport/correction_audit/pilot"
    audit_dir = "results/phase19_transport/correction_audit"
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(audit_dir, exist_ok=True)
    
    adapter = Corrected50kmTransportAdapter("results/phase18_grid_audit/india_50km_grid.csv")
    print(f"Loaded Corrected 50 km Adapter with {adapter.n_cells} source cells.")
    
    # Load ERA5 2021 NetCDF
    nc_path = "data/raw/era5/2021/era5_2021_instant.nc"
    ds = nc.Dataset(nc_path)
    raw_lats = ds.variables['latitude'][:]
    raw_lons = ds.variables['longitude'][:]
    raw_times = ds.variables['valid_time'][:]
    dt_times = pd.to_datetime(raw_times, unit='s', utc=True)
    
    flip_lats = raw_lats[0] > raw_lats[-1]
    sorted_lats = raw_lats[::-1] if flip_lats else raw_lats
    
    # Select 28 synoptic steps (Sep 15 00:00 to Sep 21 18:00 UTC, 2021)
    mask_pilot = (dt_times >= '2021-09-15 00:00:00+00:00') & (dt_times <= '2021-09-21 18:00:00+00:00')
    step_indices = [i for i, m in enumerate(mask_pilot) if m]
    selected_steps_count = len(step_indices)
    print(f"Selected {selected_steps_count} synoptic steps for corrected pilot execution.")
    
    t0_wall = time.perf_counter()
    t0_cpu = time.process_time()
    
    # Pre-cache RegularGridInterpolators for all steps in the window plus 4 steps forward (for 24h lookahead)
    max_step_needed = step_indices[-1] + 5
    print("Pre-interpolating ERA5 wind field slices...")
    interpolators_u = {}
    interpolators_v = {}
    
    for s_idx in range(step_indices[0], min(len(dt_times), max_step_needed + 1)):
        u_slice = ds.variables['u10'][s_idx, :, :]
        v_slice = ds.variables['v10'][s_idx, :, :]
        u_sorted = u_slice[::-1, :] if flip_lats else u_slice
        v_sorted = v_slice[::-1, :] if flip_lats else v_slice
        
        iu = RegularGridInterpolator((sorted_lats, raw_lons), u_sorted, bounds_error=False, fill_value=None)
        iv = RegularGridInterpolator((sorted_lats, raw_lons), v_sorted, bounds_error=False, fill_value=None)
        interpolators_u[s_idx] = iu
        interpolators_v[s_idx] = iv
        
    print("Executing dynamic trajectory advection across all 28 synoptic steps...")
    
    # Accumulator: (src_gid, dest_gid, window) -> particle count
    matrix_accum = {}
    
    for s_i, step_global_idx in enumerate(step_indices):
        # 5 sequential 6-hourly slices for [t0, t0+6h, t0+12h, t0+18h, t0+24h]
        u_slices = [interpolators_u[step_global_idx + k] for k in range(5)]
        v_slices = [interpolators_v[step_global_idx + k] for k in range(5)]
        valid_times = [0.0, 6.0, 12.0, 18.0, 24.0]
        
        horizon_dests = adapter.integrate_trajectories(
            u_slices, v_slices, valid_times, synoptic_step_idx=step_global_idx, dt_int_hours=1.0
        )
        
        for w in WINDOWS:
            dest_mat = horizon_dests[w] # (n_cells, 10)
            for src_idx in range(adapter.n_cells):
                src_gid = adapter.cell_ids[src_idx]
                row_dests = dest_mat[src_idx, :]
                u_d, cnts = np.unique(row_dests, return_counts=True)
                for d_gid, cnt in zip(u_d, cnts):
                    key = (src_gid, d_gid, w)
                    matrix_accum[key] = matrix_accum.get(key, 0) + cnt
                    
        if (s_i + 1) % 7 == 0 or (s_i + 1) == selected_steps_count:
            print(f"  Completed {s_i + 1}/{selected_steps_count} dynamic synoptic steps...")
            
    # Aggregate matrix
    print("\nAggregating corrected pilot transport matrix...")
    matrix_rows = []
    closure_records = []
    total_denominator = selected_steps_count * N_ENSEMBLE
    
    src_win_groups = {}
    for (src_gid, d_gid, w), total_cnt in matrix_accum.items():
        sw_key = (src_gid, w)
        if sw_key not in src_win_groups:
            src_win_groups[sw_key] = []
        src_win_groups[sw_key].append((d_gid, total_cnt))
        
    for (src_gid, w), d_list in src_win_groups.items():
        sum_frac = 0.0
        src_lat, src_lon = adapter.coords_lookup[src_gid]
        
        for d_gid, total_cnt in d_list:
            mean_frac = total_cnt / float(total_denominator)
            sum_frac += mean_frac
            
            if d_gid.startswith("IND_50KM"):
                d_lat, d_lon = adapter.coords_lookup[d_gid]
                dist_km = calculate_haversine_distance_km(src_lat, src_lon, d_lat, d_lon)
            else:
                dist_km = np.nan
                
            matrix_rows.append({
                'source_grid_id': src_gid,
                'dest_grid_id': d_gid,
                'elapsed_time_hours': float(w),
                'mean_transport_fraction': round(mean_frac, 6),
                'distance_km': round(dist_km, 2) if not np.isnan(dist_km) else np.nan,
                'eligible_steps_count': selected_steps_count,
                'transported_particles_count': total_cnt,
                'total_possible_particles': total_denominator
            })
            
        closure_err = abs(sum_frac - 1.0)
        closure_records.append({
            'source_grid_id': src_gid,
            'elapsed_time_hours': float(w),
            'sum_transport_fraction': round(sum_frac, 8),
            'closure_error': closure_err,
            'closure_passed': closure_err < 1e-12
        })
        
    df_matrix_corr = pd.DataFrame(matrix_rows)
    df_matrix_corr = df_matrix_corr.sort_values(
        by=['source_grid_id', 'elapsed_time_hours', 'mean_transport_fraction'],
        ascending=[True, True, False]
    ).reset_index(drop=True)
    
    t1_wall = time.perf_counter()
    wall_sec = t1_wall - t0_wall
    
    out_matrix_csv = os.path.join(out_dir, "transport_matrix_pilot_corrected_50km.csv")
    df_matrix_corr.to_csv(out_matrix_csv, index=False)
    print(f"Saved corrected pilot matrix: {out_matrix_csv} ({len(df_matrix_corr):,} rows)")
    
    # Comparison against old pilot matrix
    old_pilot_csv = "results/phase19_transport/pilot/transport_matrix_pilot_50km.csv"
    if os.path.exists(old_pilot_csv):
        print("\n--- Direct Comparison: Old Frozen-Wind Pilot vs Corrected Dynamic Pilot ---")
        df_matrix_old = pd.read_csv(old_pilot_csv)
        
        # Core cities comparison at 24h
        core_cities = {
            'Delhi': 'IND_50KM_r045_c018',
            'Kanpur': 'IND_50KM_r041_c024',
            'Kolkata': 'IND_50KM_r033_c040',
            'Mumbai': 'IND_50KM_r025_c009',
            'Bengaluru': 'IND_50KM_r011_c018'
        }
        
        comp_rows = []
        for city, cid in core_cities.items():
            # Old 24h top destination
            sub_old = df_matrix_old[(df_matrix_old['source_grid_id'] == cid) & (df_matrix_old['elapsed_time_hours'] == 24.0)]
            self_old = sub_old[sub_old['dest_grid_id'] == cid]['mean_transport_fraction'].values
            self_old_val = self_old[0] if len(self_old) > 0 else 0.0
            top_dest_old = sub_old.iloc[0]['dest_grid_id']
            top_frac_old = sub_old.iloc[0]['mean_transport_fraction']
            
            # Corrected 24h top destination
            sub_corr = df_matrix_corr[(df_matrix_corr['source_grid_id'] == cid) & (df_matrix_corr['elapsed_time_hours'] == 24.0)]
            self_corr = sub_corr[sub_corr['dest_grid_id'] == cid]['mean_transport_fraction'].values
            self_corr_val = self_corr[0] if len(self_corr) > 0 else 0.0
            top_dest_corr = sub_corr.iloc[0]['dest_grid_id']
            top_frac_corr = sub_corr.iloc[0]['mean_transport_fraction']
            
            comp_rows.append({
                'city': city,
                'grid_id': cid,
                'old_top_dest_24h': top_dest_old,
                'old_top_fraction_24h': top_frac_old,
                'old_self_retention_24h': self_old_val,
                'corrected_top_dest_24h': top_dest_corr,
                'corrected_top_fraction_24h': top_frac_corr,
                'corrected_self_retention_24h': self_corr_val,
                'top_destination_changed': top_dest_old != top_dest_corr
            })
            
        df_comp = pd.DataFrame(comp_rows)
        comp_csv = os.path.join(audit_dir, "comparison_old_vs_corrected.csv")
        df_comp.to_csv(comp_csv, index=False)
        print(df_comp[['city', 'old_top_dest_24h', 'corrected_top_dest_24h', 'top_destination_changed']].to_string(index=False))
        print(f"\nSaved comparison table: {comp_csv}")
        
    # Profile
    df_closure = pd.DataFrame(closure_records)
    max_err = df_closure['closure_error'].max()
    pass_rate = (df_closure['closure_passed'].sum() / len(df_closure)) * 100.0
    
    profile_data = [
        {"metric": "Dynamic Integration Time Step", "value": "1.0", "unit": "Hours"},
        {"metric": "Total Slices Evaluated", "value": f"{adapter.n_cells * selected_steps_count:,}", "unit": "Source-Time Slices"},
        {"metric": "Total Trajectories Simulated", "value": f"{adapter.n_cells * selected_steps_count * N_ENSEMBLE:,}", "unit": "Trajectories"},
        {"metric": "Total Wall-Clock Runtime", "value": f"{wall_sec:.2f}", "unit": "Seconds"},
        {"metric": "Average Step Runtime", "value": f"{wall_sec / selected_steps_count:.2f}", "unit": "Seconds / Synoptic Step"},
        {"metric": "Corrected Matrix Rows", "value": f"{len(df_matrix_corr):,}", "unit": "Pairs"},
        {"metric": "Max Closure Error", "value": f"{max_err:.2e}", "unit": "Abs Error"},
        {"metric": "Closure Pass Rate", "value": f"{pass_rate:.2f}%", "unit": "Percent"}
    ]
    df_profile = pd.DataFrame(profile_data)
    profile_csv = os.path.join(out_dir, "pilot_corrected_profile.csv")
    df_profile.to_csv(profile_csv, index=False)
    print(f"Saved pilot corrected profile: {profile_csv}")

if __name__ == '__main__':
    main()
