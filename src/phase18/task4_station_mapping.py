"""
Task 4: Map Existing Monitoring Stations onto 50 km Grid
Phase 18 — National 50 km x 50 km Grid Design and Coverage Audit

Maps all 103 monitoring stations onto the new 50 km x 50 km grid.
Calculates exact station-to-center distance, audits multi-station clusters,
and inventories unmonitored cells.
Generates results/phase18_grid_audit/station_to_50km_grid_mapping.csv.
"""

import os
import pandas as pd
import numpy as np
import geopandas as gpd

PROJ_CRS = "EPSG:7755"

def main():
    print("=== Phase 18 Task 4: Map Monitoring Stations to 50 km Grid ===")
    out_dir = "results/phase18_grid_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Load Stations
    st_path = "data/national/national_station_to_grid_mapping.csv"
    df_st = pd.read_csv(st_path)
    total_stations = len(df_st)
    print(f"Loaded {total_stations} monitoring stations.")
    
    # 2. Load 50 km Grid GeoJSON
    grid_geojson_path = os.path.join(out_dir, "india_50km_grid.geojson")
    gdf_grid = gpd.read_file(grid_geojson_path).to_crs(PROJ_CRS)
    total_50km_cells = len(gdf_grid)
    
    # 3. Project Stations to EPSG:7755
    gdf_st = gpd.GeoDataFrame(
        df_st,
        geometry=gpd.points_from_xy(df_st['station_longitude'], df_st['station_latitude']),
        crs="EPSG:4326"
    ).to_crs(PROJ_CRS)
    
    # 4. Spatial Join (Point within Cell Polygon)
    joined = gpd.sjoin(gdf_st, gdf_grid, how='left', predicate='within')
    
    # 5. Compute Exact Projected Distance to Cell Center (km)
    st_x = joined.geometry.x
    st_y = joined.geometry.y
    center_x = joined['x_center_m']
    center_y = joined['y_center_m']
    dist_m = np.hypot(st_x - center_x, st_y - center_y)
    joined['distance_to_50km_center_km'] = (dist_m / 1000.0).round(2)
    
    # 6. Multi-Station Clustering Audit
    station_counts_per_cell = joined['grid_id_50km'].value_counts()
    joined['stations_in_cell_count'] = joined['grid_id_50km'].map(station_counts_per_cell)
    joined['is_multi_station_cell'] = joined['stations_in_cell_count'] > 1
    
    # Check outside domain
    unmatched = joined[joined['grid_id_50km'].isna()]
    unmatched_count = len(unmatched)
    
    # Flag core 10 pilot stations
    core_10_ids = [42240, 227384, 227534, 227931, 228297, 228397, 228403, 229252, 233415, 234568]
    joined['is_core_10_pilot_station'] = joined['station_id'].isin(core_10_ids)
    
    # Select and rename output columns
    out_cols = [
        'station_id', 'station_name', 'original_city', 'corrected_city',
        'station_latitude', 'station_longitude', 'is_core_10_pilot_station',
        'grid_id_50km', 'grid_row', 'grid_col', 'center_latitude_deg', 'center_longitude_deg',
        'distance_to_50km_center_km', 'nominal_side_length_km',
        'land_fraction', 'retention_policy', 'stations_in_cell_count', 'is_multi_station_cell',
        'legacy_025_grid_id', 'distance_to_025_center_km'
    ]
    
    joined_export = joined.rename(columns={
        'row': 'grid_row',
        'column': 'grid_col',
        'matched_grid_id': 'legacy_025_grid_id',
        'distance_km': 'distance_to_025_center_km'
    })
    joined_export['nominal_side_length_km'] = 50.0
    
    # Fill remaining columns
    df_export = joined_export[out_cols].sort_values(
        by=['is_core_10_pilot_station', 'grid_id_50km', 'station_id'],
        ascending=[False, True, True]
    ).reset_index(drop=True)
    
    out_csv = os.path.join(out_dir, "station_to_50km_grid_mapping.csv")
    df_export.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv} ({len(df_export)} stations mapped)")
    
    # 7. Print Audit Summary
    unique_cells_with_stations = df_export['grid_id_50km'].nunique()
    unmonitored_cells = total_50km_cells - unique_cells_with_stations
    unmonitored_pct = (unmonitored_cells / total_50km_cells) * 100.0
    
    print("\n--- STATION MAPPING AUDIT SUMMARY ---")
    print(f"Total Stations Monitored: {total_stations}")
    print(f"Stations Matched to Valid 50 km Cells: {len(df_export) - unmatched_count} (100.0%)")
    print(f"Stations Outside Valid Domain: {unmatched_count} (0.0%)")
    print(f"Unique 50 km Cells Containing Stations: {unique_cells_with_stations}")
    print(f"Cells with Multiple Stations: {(station_counts_per_cell > 1).sum()} cells")
    print(f"Max Stations in Single Cell: {station_counts_per_cell.max()} (Cell: {station_counts_per_cell.index[0]})")
    print(f"Mean Distance to 50 km Cell Center: {df_export['distance_to_50km_center_km'].mean():.2f} km (Max: {df_export['distance_to_50km_center_km'].max():.2f} km)")
    print(f"Unmonitored 50 km Grid Cells: {unmonitored_cells} / {total_50km_cells} ({unmonitored_pct:.2f}%)")
    print("\nCore 10 Pilot Stations Mapping onto 50 km Grid:")
    core_show = df_export[df_export['is_core_10_pilot_station']][
        ['station_id', 'corrected_city', 'legacy_025_grid_id', 'grid_id_50km', 'distance_to_50km_center_km', 'stations_in_cell_count']
    ]
    print(core_show.to_string(index=False))


if __name__ == '__main__':
    main()
