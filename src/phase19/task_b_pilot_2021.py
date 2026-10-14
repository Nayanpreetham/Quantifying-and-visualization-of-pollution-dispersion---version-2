"""
Task B: Representative Pilot on 50 km Grid (Benchmark Year 2021)
Phase 19 — National 50 km Grid-to-Grid Pollution Transport

Executes a controlled, reproducible pilot on the 50 km x 50 km grid for year 2021:
- Covers all 1,380 source cells (both 51 monitored and 1,329 unmonitored).
- Uses 28 representative synoptic steps across diurnal cycles (00, 06, 12, 18 UTC)
  in the verified September 2021 validation period (2021-09-15 00:00 to 2021-09-21 18:00 UTC).
- Evaluates all 5 advection horizons (1h, 3h, 6h, 12h, 24h).
- Records wall-clock runtime, CPU utilization, memory, and closure.
- Produces results/phase19_transport/pilot/ artifacts.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
import tracemalloc
import netCDF4 as nc
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from src.phase19.transport_adapter_50km import (
    National50kmTransportAdapter,
    calculate_haversine_distance_km,
    WINDOWS,
    N_ENSEMBLE
)

def main():
    print("=== Phase 19 Task B: Representative Pilot on 50 km Grid (Year 2021) ===")
    out_dir = "results/phase19_transport/pilot"
    os.makedirs(out_dir, exist_ok=True)
    
    # Process profiler setup
    tracemalloc.start()
    t0_wall = time.perf_counter()
    t0_cpu = time.process_time()
    
    # 1. Initialize 50 km Transport Adapter
    adapter = National50kmTransportAdapter("results/phase18_grid_audit/india_50km_grid.csv")
    print(f"Loaded 50 km Adapter with {adapter.n_cells} terrestrial source cells.")
    
    # 2. Load ERA5 2021 Instant NetCDF
    nc_path = "data/raw/era5/2021/era5_2021_instant.nc"
    if not os.path.exists(nc_path):
        raise FileNotFoundError(f"ERA5 file missing: {nc_path}")
        
    ds = nc.Dataset(nc_path)
    raw_lats = ds.variables['latitude'][:]
    raw_lons = ds.variables['longitude'][:]
    raw_times = ds.variables['valid_time'][:]
    dt_times = pd.to_datetime(raw_times, unit='s', utc=True)
    
    # Align lats ascending for RegularGridInterpolator
    flip_lats = raw_lats[0] > raw_lats[-1]
    sorted_lats = raw_lats[::-1] if flip_lats else raw_lats
    
    # 3. Select Representative 28 Synoptic Steps (Sep 15 00:00 to Sep 21 18:00 UTC, 2021)
    mask_pilot = (dt_times >= '2021-09-15 00:00:00+00:00') & (dt_times <= '2021-09-21 18:00:00+00:00')
    step_indices = [i for i, m in enumerate(mask_pilot) if m]
    selected_steps_count = len(step_indices)
    print(f"Selected {selected_steps_count} synoptic steps for pilot execution (2021-09-15 to 2021-09-21).")
    
    # Save machine-readable configuration
    pilot_config = {
        "phase": 19,
        "task": "Task B — Representative 50 km Pilot",
        "benchmark_year": 2021,
        "pilot_start_utc": str(dt_times[step_indices[0]]),
        "pilot_end_utc": str(dt_times[step_indices[-1]]),
        "synoptic_steps_count": selected_steps_count,
        "total_source_cells": adapter.n_cells,
        "monitored_source_cells": 51,
        "unmonitored_source_cells": adapter.n_cells - 51,
        "advection_windows_hours": WINDOWS,
        "ensemble_members": N_ENSEMBLE,
        "crs": "EPSG:7755",
        "grid_resolution_m": 50000.0,
        "random_seed_base": 42
    }
    config_path = os.path.join(out_dir, "pilot_config.json")
    with open(config_path, "w") as f:
        json.dump(pilot_config, f, indent=2)
    print(f"Saved machine-readable pilot config: {config_path}")
    
    # 4. Execute Pilot Trajectory Simulation
    print("\nExecuting Lagrangian ensemble dispersion across all 1,380 cells...")
    
    # Step-level records accumulator: key -> (src, dest, window) -> count sum
    matrix_accum = {} # (src, dest, window) -> total_particles
    source_window_steps = {} # (src, window) -> eligible_steps
    step_run_records = []
    
    for s_idx, step_global_idx in enumerate(step_indices):
        t_str = str(dt_times[step_global_idx])
        
        # Load u10 and v10 slices for this step
        u_slice = ds.variables['u10'][step_global_idx, :, :]
        v_slice = ds.variables['v10'][step_global_idx, :, :]
        
        u_sorted = u_slice[::-1, :] if flip_lats else u_slice
        v_sorted = v_slice[::-1, :] if flip_lats else v_slice
        
        interp_u = RegularGridInterpolator((sorted_lats, raw_lons), u_sorted, bounds_error=False, fill_value=None)
        interp_v = RegularGridInterpolator((sorted_lats, raw_lons), v_sorted, bounds_error=False, fill_value=None)
        
        step_results = adapter.simulate_synoptic_step(interp_u, interp_v, step_global_idx, t_str)
        
        # Accumulate
        for src_gid, d_gid, w, cnt, frac in step_results:
            key = (src_gid, d_gid, w)
            matrix_accum[key] = matrix_accum.get(key, 0) + cnt
            
        for src_gid in adapter.cell_ids:
            for w in WINDOWS:
                sw_key = (src_gid, w)
                source_window_steps[sw_key] = source_window_steps.get(sw_key, 0) + 1
                
        if (s_idx + 1) % 7 == 0 or (s_idx + 1) == selected_steps_count:
            print(f"  Completed {s_idx + 1}/{selected_steps_count} synoptic steps...")
            
    # 5. Build Aggregated Transport Matrix (Phase 10 standard unconditional pooling)
    print("\nAggregating pilot transport matrix with unconditional step normalization...")
    matrix_rows = []
    closure_records = []
    
    # Group accumulator by (src, window) to verify closure
    src_win_groups = {}
    for (src_gid, d_gid, w), total_cnt in matrix_accum.items():
        sw_key = (src_gid, w)
        if sw_key not in src_win_groups:
            src_win_groups[sw_key] = []
        src_win_groups[sw_key].append((d_gid, total_cnt))
        
    for (src_gid, w), d_list in src_win_groups.items():
        n_eligible = source_window_steps[(src_gid, w)]
        total_denominator_particles = n_eligible * N_ENSEMBLE
        
        sum_frac = 0.0
        src_lat, src_lon = adapter.coords_lookup[src_gid]
        
        for d_gid, total_cnt in d_list:
            mean_frac = total_cnt / float(total_denominator_particles)
            sum_frac += mean_frac
            
            if d_gid != "OUTSIDE_DOMAIN":
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
                'eligible_steps_count': n_eligible,
                'transported_particles_count': total_cnt,
                'total_possible_particles': total_denominator_particles
            })
            
        closure_err = abs(sum_frac - 1.0)
        closure_records.append({
            'source_grid_id': src_gid,
            'elapsed_time_hours': float(w),
            'sum_transport_fraction': round(sum_frac, 8),
            'closure_error': closure_err,
            'closure_passed': closure_err < 1e-12
        })
        
    df_matrix = pd.DataFrame(matrix_rows)
    df_closure = pd.DataFrame(closure_records)
    
    # Sort matrix logically
    df_matrix = df_matrix.sort_values(
        by=['source_grid_id', 'elapsed_time_hours', 'mean_transport_fraction'],
        ascending=[True, True, False]
    ).reset_index(drop=True)
    
    # 6. Profiling Measurements
    t1_wall = time.perf_counter()
    t1_cpu = time.process_time()
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    ram_peak_mb = peak_mem / 1e6
    
    wall_sec = t1_wall - t0_wall
    cpu_sec = t1_cpu - t0_cpu
    total_source_time_slices = adapter.n_cells * selected_steps_count
    total_evals = total_source_time_slices * len(WINDOWS)
    total_trajectories = total_source_time_slices * N_ENSEMBLE
    
    throughput_slices_sec = total_source_time_slices / wall_sec
    
    # Save outputs
    matrix_out_csv = os.path.join(out_dir, "transport_matrix_pilot_50km.csv")
    df_matrix.to_csv(matrix_out_csv, index=False)
    
    closure_out_csv = os.path.join(out_dir, "pilot_closure_audit.csv")
    df_closure.to_csv(closure_out_csv, index=False)
    
    profile_data = [
        {"metric": "Total Source Cells Evaluated", "value": f"{adapter.n_cells}", "unit": "Cells"},
        {"metric": "Synoptic Slices Executed", "value": f"{total_source_time_slices:,}", "unit": "Source-Time Slices"},
        {"metric": "Window Evaluations", "value": f"{total_evals:,}", "unit": "Window Evaluations"},
        {"metric": "Lagrangian Trajectories Simulated", "value": f"{total_trajectories:,}", "unit": "Trajectories"},
        {"metric": "Wall-Clock Runtime", "value": f"{wall_sec:.2f}", "unit": "Seconds"},
        {"metric": "CPU Process Time", "value": f"{cpu_sec:.2f}", "unit": "Seconds"},
        {"metric": "Throughput Rate", "value": f"{throughput_slices_sec:.1f}", "unit": "Slices / Second"},
        {"metric": "Peak Traced Memory", "value": f"{ram_peak_mb:.1f}", "unit": "MB"},
        {"metric": "Aggregated Matrix Rows", "value": f"{len(df_matrix):,}", "unit": "Pairs"},
        {"metric": "Max Probability Closure Error", "value": f"{df_closure['closure_error'].max():.2e}", "unit": "Abs Error"},
        {"metric": "Closure Groups Audited", "value": f"{len(df_closure):,}", "unit": "Source-Window Groups"},
        {"metric": "Closure Pass Rate", "value": f"{(df_closure['closure_passed'].sum() / len(df_closure)) * 100:.2f}%", "unit": "Percent"}
    ]
    df_profile = pd.DataFrame(profile_data)
    profile_out_csv = os.path.join(out_dir, "pilot_execution_profile.csv")
    df_profile.to_csv(profile_out_csv, index=False)
    
    print("\n--- PILOT EXECUTION PROFILE ---")
    print(df_profile.to_string(index=False))
    print(f"\nSaved pilot matrix: {matrix_out_csv} ({len(df_matrix)} rows)")
    print(f"Saved closure audit: {closure_out_csv} ({len(df_closure)} groups)")
    print(f"Saved execution profile: {profile_out_csv}")


if __name__ == '__main__':
    main()
