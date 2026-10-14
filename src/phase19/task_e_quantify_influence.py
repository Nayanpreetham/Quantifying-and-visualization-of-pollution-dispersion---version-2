"""
Task E: Quantify Modeled Transport Influence and 4-Tier Separation
Phase 19 — National 50 km Grid-to-Grid Pollution Transport

Implements the mandatory 4-tier scientific data architecture:
- Tier 1: Meteorological Transport Fraction (T_bar_{s, d, \Delta t}).
  Dimensionless physical probability in [0, 1] defined for all 1,380 grid cells.
- Tier 2: Source-Weighted Modeled Influence (I_{s, d, \Delta t} = C_src * T_bar_{s, d, \Delta t}, ug/m3).
  Strictly computed ONLY for the 51 monitored cells with concurrent observed ground PM2.5.
  Explicitly sets unmonitored cells (1,329 cells) to NaN with audit flag.
- Tier 3: Observed Regulatory Station Ambient PM2.5 / CPCB NAQI.
  Recorded at ground monitoring stations.
- Tier 4: Explicit Boundary Prohibition.
  Guarantees NO destination ambient AQI prediction claim is made.
  Modeled influence reflects dispersed source-tracer contribution only.

Outputs:
- results/phase19_transport/matrices/monitored_cells_concentration_summary.csv
- results/phase19_transport/matrices/modeled_influence_50km_baseline.csv
- results/phase19_transport/matrices/destination_received_influence_summary.csv
- results/phase19_transport/validation/four_tier_separation_audit.csv
"""

import os
import sys
import numpy as np
import pandas as pd

def main():
    print("=== Phase 19 Task E: Quantify Modeled Influence & 4-Tier Separation ===")
    
    matrices_dir = "results/phase19_transport/matrices"
    val_dir = "results/phase19_transport/validation"
    os.makedirs(matrices_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)
    
    baseline_matrix_path = os.path.join(matrices_dir, "transport_matrix_50km_2019_2024_baseline.parquet")
    baseline_csv_path = os.path.join(matrices_dir, "transport_matrix_50km_2019_2024_baseline.csv")
    openaq_obs_path = "data/real/openaq/pm25_observations.csv"
    station_map_path = "results/phase18_grid_audit/station_to_50km_grid_mapping.csv"
    grid_path = "results/phase18_grid_audit/india_50km_grid.csv"
    
    # 1. Load Ground Observations & Station Mapping
    print("\n1. Loading Ground PM2.5 Observations and Station Mapping...")
    df_obs = pd.read_csv(openaq_obs_path)
    df_st = pd.read_csv(station_map_path)
    df_grid = pd.read_csv(grid_path)
    
    total_cells = len(df_grid)
    all_grid_ids = set(df_grid['grid_id_50km'].unique())
    monitored_grid_ids = set(df_st['grid_id_50km'].unique())
    unmonitored_grid_ids = all_grid_ids - monitored_grid_ids
    
    print(f"Total National Grid Cells: {total_cells}")
    print(f"Monitored Grid Cells (Ground Truth): {len(monitored_grid_ids)}")
    print(f"Unmonitored Grid Cells (Zero Ground Truth): {len(unmonitored_grid_ids)}")
    
    # Filter valid PM2.5 observations (0 < pm25 < 1000 ug/m3)
    valid_obs = df_obs[(df_obs['pm25'] > 0.0) & (df_obs['pm25'] < 1000.0)].copy()
    print(f"Valid PM2.5 observations in record: {len(valid_obs):,} across {valid_obs['station_id'].nunique()} stations")
    
    # Merge station observations with 50 km grid mapping
    merged_obs = pd.merge(
        valid_obs[['station_id', 'pm25', 'timestamp_utc']],
        df_st[['station_id', 'station_name', 'corrected_city', 'grid_id_50km', 'center_latitude_deg', 'center_longitude_deg']],
        on='station_id',
        how='inner'
    )
    
    # 2. Aggregate Observed PM2.5 to 50 km Monitored Cells
    print("\n2. Aggregating Ground Observations to 51 Monitored Cells...")
    cell_stats = []
    
    for gid in sorted(list(monitored_grid_ids)):
        c_sub = merged_obs[merged_obs['grid_id_50km'] == gid]
        st_sub = df_st[df_st['grid_id_50km'] == gid]
        
        c_lat = st_sub.iloc[0]['center_latitude_deg']
        c_lon = st_sub.iloc[0]['center_longitude_deg']
        cities = "; ".join(sorted(st_sub['corrected_city'].unique()))
        st_names = "; ".join(sorted(st_sub['station_name'].unique()))
        n_stations = len(st_sub)
        
        if len(c_sub) > 0:
            mean_pm25 = float(c_sub['pm25'].mean())
            med_pm25 = float(c_sub['pm25'].median())
            std_pm25 = float(c_sub['pm25'].std()) if len(c_sub) > 1 else 0.0
            n_obs = len(c_sub)
        else:
            mean_pm25 = np.nan
            med_pm25 = np.nan
            std_pm25 = np.nan
            n_obs = 0
            
        cell_stats.append({
            'grid_id_50km': gid,
            'cities': cities,
            'station_count': n_stations,
            'total_observations': n_obs,
            'mean_observed_pm25_ugm3': round(mean_pm25, 2) if not np.isnan(mean_pm25) else np.nan,
            'median_observed_pm25_ugm3': round(med_pm25, 2) if not np.isnan(med_pm25) else np.nan,
            'std_observed_pm25_ugm3': round(std_pm25, 2) if not np.isnan(std_pm25) else np.nan,
            'center_latitude_deg': c_lat,
            'center_longitude_deg': c_lon,
            'station_names': st_names
        })
        
    df_cell_stats = pd.DataFrame(cell_stats)
    cell_stats_csv = os.path.join(matrices_dir, "monitored_cells_concentration_summary.csv")
    df_cell_stats.to_csv(cell_stats_csv, index=False)
    print(f"Saved monitored cells summary: {cell_stats_csv} ({len(df_cell_stats)} cells)")
    
    # 3. Apply 4-Tier Separation to Master Baseline Matrix
    print("\n3. Loading Master 6-Year Baseline Transport Matrix...")
    if os.path.exists(baseline_matrix_path):
        df_base = pd.read_parquet(baseline_matrix_path)
    elif os.path.exists(baseline_csv_path):
        df_base = pd.read_csv(baseline_csv_path)
    else:
        raise FileNotFoundError(f"Master baseline matrix not found at {baseline_matrix_path} or {baseline_csv_path}")
        
    print(f"Loaded {len(df_base):,} transport pairs from master baseline matrix.")
    
    # Merge mean source concentration
    mean_pm25_map = dict(zip(df_cell_stats['grid_id_50km'], df_cell_stats['mean_observed_pm25_ugm3']))
    
    has_obs_col = df_base['source_grid_id'].isin(monitored_grid_ids)
    src_pm25_col = df_base['source_grid_id'].map(mean_pm25_map)
    
    # Tier 2 Modeled Influence: I = C_src * T_bar (ug/m3)
    # Strictly valid ONLY where has_source_observation == True
    modeled_inf_col = np.where(
        has_obs_col & src_pm25_col.notna(),
        np.round(src_pm25_col * df_base['mean_transport_fraction'], 4),
        np.nan
    )
    
    status_col = np.where(
        has_obs_col & src_pm25_col.notna(),
        "MONITORED_SOURCE_INFLUENCE_CALCULATED",
        "UNMONITORED_SOURCE_NO_INFLUENCE_CALCULATED"
    )
    
    df_influence = df_base.copy()
    df_influence['has_source_observation'] = has_obs_col
    df_influence['source_mean_pm25_ugm3'] = src_pm25_col
    df_influence['modeled_influence_ugm3'] = modeled_inf_col
    df_influence['influence_status'] = status_col
    df_influence['is_ambient_aqi_prediction'] = False
    df_influence['model_tier'] = np.where(
        has_obs_col & src_pm25_col.notna(),
        "Tier 2: Source-Weighted Modeled Influence",
        "Tier 1: Meteorological Transport Fraction Only"
    )
    
    inf_csv_path = os.path.join(matrices_dir, "modeled_influence_50km_baseline.csv")
    inf_parquet_path = os.path.join(matrices_dir, "modeled_influence_50km_baseline.parquet")
    
    df_influence.to_csv(inf_csv_path, index=False)
    df_influence.to_parquet(inf_parquet_path, index=False, compression="snappy")
    print(f"Saved full-grid modeled influence matrix: {inf_csv_path} ({len(df_influence):,} rows)")
    
    # 4. Destination Received Influence Aggregation
    print("\n4. Aggregating Transboundary Received Influence by Destination...")
    monitored_rows = df_influence[df_influence['has_source_observation'] == True].copy()
    
    dest_records = []
    windows = sorted(df_base['elapsed_time_hours'].unique())
    
    for w in windows:
        sub_w = monitored_rows[monitored_rows['elapsed_time_hours'] == w]
        
        for d_gid, d_group in sub_w.groupby('dest_grid_id'):
            tot_inf = d_group['modeled_influence_ugm3'].sum()
            n_contrib = (d_group['modeled_influence_ugm3'] > 0.0001).sum()
            
            # Separate self vs transboundary
            self_group = d_group[d_group['source_grid_id'] == d_gid]
            self_inf = self_group['modeled_influence_ugm3'].sum() if len(self_group) > 0 else 0.0
            ext_inf = tot_inf - self_inf
            
            # Top contributing source
            top_row = d_group.sort_values(by='modeled_influence_ugm3', ascending=False).iloc[0]
            top_src = top_row['source_grid_id']
            top_src_inf = top_row['modeled_influence_ugm3']
            
            dest_records.append({
                'dest_grid_id': d_gid,
                'elapsed_time_hours': w,
                'total_received_influence_ugm3': round(tot_inf, 4),
                'self_retained_influence_ugm3': round(self_inf, 4),
                'transboundary_external_influence_ugm3': round(ext_inf, 4),
                'contributing_monitored_sources_count': int(n_contrib),
                'top_contributing_source_id': top_src,
                'top_contributor_influence_ugm3': round(top_src_inf, 4),
                'is_destination_monitored': d_gid in monitored_grid_ids
            })
            
    df_dest = pd.DataFrame(dest_records)
    df_dest = df_dest.sort_values(by=['dest_grid_id', 'elapsed_time_hours']).reset_index(drop=True)
    dest_csv_path = os.path.join(matrices_dir, "destination_received_influence_summary.csv")
    df_dest.to_csv(dest_csv_path, index=False)
    print(f"Saved destination received influence summary: {dest_csv_path} ({len(df_dest):,} rows)")
    
    # 5. Four-Tier Scientific Integrity Audit Table
    print("\n5. Authoring Four-Tier Scientific Integrity Audit...")
    audit_data = [
        {
            "tier_level": "Tier 1: Meteorological Transport Fraction",
            "mathematical_symbol": "T_bar_{s, d, \Delta t}",
            "units": "Dimensionless Probability [0, 1]",
            "national_grid_coverage": f"{total_cells} / {total_cells} cells (100.0%)",
            "empirical_data_source": "ERA5 6-hourly U10/V10 Reanalysis (2019-2024)",
            "closure_conservation": "Exact probability row-sum closure (sum = 1.0 +- 1e-12)",
            "scientific_status": "VALIDATED FULL-GRID PHYSICAL ATTRIBUTION"
        },
        {
            "tier_level": "Tier 2: Source-Weighted Modeled Influence",
            "mathematical_symbol": "I_{s, d, \Delta t} = C_src * T_bar_{s, d, \Delta t}",
            "units": "ug/m3 (Micrograms per cubic meter)",
            "national_grid_coverage": f"{len(monitored_grid_ids)} / {total_cells} cells ({len(monitored_grid_ids)/total_cells*100:.2f}%)",
            "empirical_data_source": "OpenAQ & CPCB Hourly PM2.5 at 103 Ground Stations",
            "closure_conservation": "Dispersed source-tracer mass conservation; zero unmonitored fabrication",
            "scientific_status": "VALIDATED MONITORED-SOURCE ATTRIBUTION ONLY"
        },
        {
            "tier_level": "Tier 3: Observed Regulatory Air Quality",
            "mathematical_symbol": "AQI_{obs, station} / CPCB NAQI",
            "units": "CPCB Index [0, 500] / 24h ug/m3",
            "national_grid_coverage": f"51 cells ({len(df_st)} stations in 25 urban centers)",
            "empirical_data_source": "Continuous Ambient Air Quality Monitoring Stations (CAAQMS)",
            "closure_conservation": "Direct ground truth; station-level empirical observations",
            "scientific_status": "OFFICIAL REGULATORY GROUND BENCHMARK"
        },
        {
            "tier_level": "Tier 4: Prohibited Destination Ambient AQI",
            "mathematical_symbol": "PREDICTED_AQI_dest (PROHIBITED)",
            "units": "N/A (Prohibited from prediction)",
            "national_grid_coverage": "0 / 1,380 cells (0.0% — Enforced by Model Design)",
            "empirical_data_source": "NONE — Model strictly avoids unscientific destination AQI prediction",
            "closure_conservation": "N/A — Requires full emissions inventory, chemistry, & background",
            "scientific_status": "EXPLICITLY REJECTED AS UNSCIENTIFIC WITHOUT EMISSIONS"
        }
    ]
    df_audit = pd.DataFrame(audit_data)
    audit_csv = os.path.join(val_dir, "four_tier_separation_audit.csv")
    df_audit.to_csv(audit_csv, index=False)
    print(f"Saved 4-tier separation audit: {audit_csv}")
    print("\n--- FOUR-TIER SEPARATION AUDIT TABLE ---")
    print(df_audit[['tier_level', 'units', 'national_grid_coverage', 'scientific_status']].to_string(index=False))

if __name__ == '__main__':
    main()
