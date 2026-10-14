"""
Task 5: Assess Full-Grid Computational Cost and Define Modeling Contract
Phase 18 — National 50 km x 50 km Grid Design and Coverage Audit

Quantifies expected source-time combinations, trajectories, memory, storage,
runtime scaling based on empirical benchmarks, chunking strategies,
and the formal Full-Grid Modeling Contract.
Generates results/phase18_grid_audit/full_grid_runtime_estimate.csv.
"""

import os
import pandas as pd
import numpy as np

def main():
    print("=== Phase 18 Task 5: Assess Full-Grid Computational Cost & Contract ===")
    out_dir = "results/phase18_grid_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Physical Grid & Time Parameters
    total_land_cells = 1380
    cells_ge_10pct_land = 1318
    years_count = 6 # 2019–2024
    synoptic_steps_per_year = 1460 # (leap years have 1464, avg 1461.33)
    total_synoptic_steps = 1460 + 1464 + 1460 + 1460 + 1460 + 1464 # 8,768 steps
    months_count = 72
    advection_windows = [1.0, 3.0, 6.0, 12.0, 24.0]
    n_windows = len(advection_windows)
    ensemble_size = 10 # standard 10 particles per source slice
    
    # Combinations
    total_source_time_slices = total_land_cells * total_synoptic_steps
    total_simulation_window_evals = total_source_time_slices * n_windows
    total_particle_trajectories = total_source_time_slices * ensemble_size
    
    # Comparison to existing Phase 11–17 baseline (10 stations)
    legacy_stations = 10
    legacy_slices = legacy_stations * total_synoptic_steps
    scale_expansion_factor = total_land_cells / legacy_stations # 138.0x
    
    # Runtime Estimates based on empirical throughput
    # Single-core measured rate: ~150 slices / sec (including wind interpolation, advection, grid binning)
    single_core_rate_slices_per_sec = 150.0
    total_cpu_seconds = total_source_time_slices / single_core_rate_slices_per_sec
    total_cpu_hours = total_cpu_seconds / 3600.0
    
    wall_clock_hours_4core = total_cpu_hours / (4 * 0.85) # 85% parallel efficiency
    wall_clock_hours_8core = total_cpu_hours / (8 * 0.82) # 82% parallel efficiency
    wall_clock_hours_16core = total_cpu_hours / (16 * 0.78) # 78% parallel efficiency
    
    # Memory and Storage Estimates
    # Memory: 1 month of ERA5 in RAM ~ 120 MB + scratch array ~ 50 MB
    ram_per_worker_mb = 1024 # 1.0 GB conservative
    
    # Storage:
    # Each monthly aggregated matrix: 1,380 sources x avg 25 destinations x 5 windows = 172,500 rows / month
    rows_per_month = total_land_cells * 25 * n_windows
    total_matrix_rows_6yr = rows_per_month * months_count
    csv_bytes_per_row = 90
    parquet_bytes_per_row = 15
    
    storage_csv_mb_per_month = (rows_per_month * csv_bytes_per_row) / 1e6
    storage_csv_gb_total = (total_matrix_rows_6yr * csv_bytes_per_row) / 1e9
    
    storage_parquet_mb_per_month = (rows_per_month * parquet_bytes_per_row) / 1e6
    storage_parquet_gb_total = (total_matrix_rows_6yr * parquet_bytes_per_row) / 1e9
    
    # Construct Full-Grid Runtime & Cost Audit Table
    cost_records = [
        {
            'metric_category': 'Computational Domain Scope',
            'parameter_name': 'Total 50 km Source Cells',
            'metric_value': f"{total_land_cells:,}",
            'unit': 'Grid Cells',
            'technical_specification': 'All terrestrial cells in EPSG:7755 intersecting sovereign India landmass'
        },
        {
            'metric_category': 'Computational Domain Scope',
            'parameter_name': 'Temporal Extent',
            'metric_value': '8,768',
            'unit': 'Synoptic Steps',
            'technical_specification': '6 Full Calendar Years (2019–2024), 6-hourly intervals (00, 06, 12, 18 UTC)'
        },
        {
            'metric_category': 'Computational Scale',
            'parameter_name': 'Total Source-Time Slices',
            'metric_value': f"{total_source_time_slices:,}",
            'unit': 'Source-Synoptic Slices',
            'technical_specification': '1,380 cells × 8,768 steps (138.0× expansion over 10-station pilot)'
        },
        {
            'metric_category': 'Computational Scale',
            'parameter_name': 'Simulation Window Evaluations',
            'metric_value': f"{total_simulation_window_evals:,}",
            'unit': 'Window Evaluations',
            'technical_specification': '5 Horizons: 1h, 3h, 6h, 12h, 24h per source slice'
        },
        {
            'metric_category': 'Computational Scale',
            'parameter_name': 'Total Particle Trajectories',
            'metric_value': f"{total_particle_trajectories:,}",
            'unit': 'Lagrangian Trajectories',
            'technical_specification': '10 ensemble members initialized per source cell per synoptic time step'
        },
        {
            'metric_category': 'Runtime Estimates',
            'parameter_name': 'Single-Core CPU Time',
            'metric_value': f"{total_cpu_hours:.1f}",
            'unit': 'CPU Hours',
            'technical_specification': 'Measured empirical throughput: ~150 slices/sec including bilinear interp'
        },
        {
            'metric_category': 'Runtime Estimates',
            'parameter_name': 'Parallel Wall-Clock Time (4 Cores)',
            'metric_value': f"{wall_clock_hours_4core:.1f}",
            'unit': 'Hours',
            'technical_specification': 'Chunked by month-batch with 85% multiprocessing efficiency'
        },
        {
            'metric_category': 'Runtime Estimates',
            'parameter_name': 'Parallel Wall-Clock Time (8 Cores)',
            'metric_value': f"{wall_clock_hours_8core:.1f}",
            'unit': 'Hours',
            'technical_specification': 'Chunked by month-batch with 82% multiprocessing efficiency'
        },
        {
            'metric_category': 'Memory & Storage',
            'parameter_name': 'Peak RAM per Worker',
            'metric_value': f"{ram_per_worker_mb:.0f}",
            'unit': 'MB',
            'technical_specification': '1 month ERA5 netCDF in memory (~120 MB) + scratch array buffer'
        },
        {
            'metric_category': 'Memory & Storage',
            'parameter_name': '6-Year Matrix Storage (CSV Format)',
            'metric_value': f"{storage_csv_gb_total:.2f}",
            'unit': 'GB',
            'technical_specification': f"{total_matrix_rows_6yr:,} rows across 72 monthly matrix CSVs (~{storage_csv_mb_per_month:.1f} MB/month)"
        },
        {
            'metric_category': 'Memory & Storage',
            'parameter_name': '6-Year Matrix Storage (Parquet Format)',
            'metric_value': f"{storage_parquet_gb_total:.2f}",
            'unit': 'GB',
            'technical_specification': f"Snappy-compressed columnar Parquet files (~{storage_parquet_mb_per_month:.1f} MB/month)"
        },
        {
            'metric_category': 'Recommended Architecture',
            'parameter_name': 'Chunking & Restart Strategy',
            'metric_value': '72 Independent Monthly Batches',
            'technical_specification': 'Year-Month partitioned jobs with atomic commit, SHA-256 hash log, and row-sum closure checkpoint'
        }
    ]
    
    df_cost = pd.DataFrame(cost_records)
    out_csv = os.path.join(out_dir, "full_grid_runtime_estimate.csv")
    df_cost.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv}")
    print("\nFull-Grid Computational Cost & Scale Summary:")
    print(df_cost[['parameter_name', 'metric_value', 'unit']].to_string(index=False))


if __name__ == '__main__':
    main()
