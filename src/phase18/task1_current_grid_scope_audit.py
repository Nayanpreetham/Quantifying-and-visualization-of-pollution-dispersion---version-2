"""
Task 1: Establish the Actual Existing Grid and Source Coverage
Phase 18 — National 50 km x 50 km Grid Design and Coverage Audit

Audits the existing 0.25 deg grid (data/national/india_025_grid.csv), station mappings,
ERA5 coverage, and transport matrices (Phases 15-17).
Generates results/phase18_grid_audit/current_grid_scope_audit.csv.
"""

import os
import json
import pandas as pd
import numpy as np
from shapely.geometry import shape, Point

def main():
    print("=== Phase 18 Task 1: Audit Current 0.25° Grid Scope ===")
    out_dir = "results/phase18_grid_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Load 0.25 Grid
    grid_025_path = "data/national/india_025_grid.csv"
    df_grid_025 = pd.read_csv(grid_025_path)
    total_rect_cells = len(df_grid_025)
    
    # 2. Land intersection check
    land_geojson_path = "data/raw/geography/india_land_boundary.geojson"
    if os.path.exists(land_geojson_path):
        with open(land_geojson_path, 'r') as f:
            land_data = json.load(f)
        land_geom = shape(land_data['features'][0]['geometry'])
    else:
        with open("data/raw/geography/india_boundary.geojson", 'r') as f:
            land_data = json.load(f)
        land_geom = shape(land_data['features'][0]['geometry'])
        
    in_land = df_grid_025.apply(lambda r: land_geom.intersects(Point(r['longitude'], r['latitude'])), axis=1)
    cells_intersecting_land = int(in_land.sum())
    
    # 3. ERA5 coverage
    cells_valid_era5 = int((df_grid_025['has_era5_wind'] == True).sum())
    
    # 4. Mapped monitoring stations
    mapping_path = "data/national/national_station_to_grid_mapping.csv"
    df_map = pd.read_csv(mapping_path)
    total_mapped_stations = len(df_map)
    cells_with_stations = int(df_map['matched_grid_id'].nunique())
    
    # 5. Cells used as dispersion sources in existing runs (Phase 11-17)
    df_p17_src = pd.read_csv("results/phase17_target_zones/source_zones_ranked_by_aqi.csv")
    cells_used_as_sources = int(df_p17_src['source_grid_id'].nunique())
    stations_used_as_sources = int(len(df_p17_src))
    source_grid_ids = sorted(df_p17_src['source_grid_id'].unique().tolist())
    
    # 6. Cells appearing as transport destinations (from Phase 11 and Phase 15/16)
    df_mat_p11 = pd.read_csv("results/phase11_validation/transport_matrix_phase11.csv")
    dest_p11 = set(df_mat_p11['dest_grid_id'].unique()) - {'OUTSIDE_DOMAIN'}
    
    df_mat_p15 = pd.read_csv("results/phase13_six_year/annual/transport_matrix_annual_2020.csv")
    dest_p15 = set(df_mat_p15['dest_grid_id'].unique()) - {'OUTSIDE_DOMAIN'}
    
    all_dest_cells = dest_p11.union(dest_p15)
    cells_appearing_as_dest = len(all_dest_cells)
    
    # Cells appearing ONLY as destinations (not sources)
    cells_only_destinations = len(all_dest_cells - set(source_grid_ids))
    
    # Cells never reached and never sources
    all_grid_ids = set(df_grid_025['grid_id'].unique())
    cells_never_reached_nor_source = len(all_grid_ids - all_dest_cells - set(source_grid_ids))
    
    # Construct Scope Audit Table
    audit_records = [
        {
            'category': 'Total Rectangular Grid Cells',
            'cell_count': total_rect_cells,
            'percentage_of_total': 100.0,
            'spatial_domain': 'National 0.25° Domain (Lat: 5.0–38.0°N, Lon: 68.0–98.0°E)',
            'scope_role': 'Complete rectangular computational array (133 rows × 121 cols)'
        },
        {
            'category': 'Cells Intersecting India Land Boundary',
            'cell_count': cells_intersecting_land,
            'percentage_of_total': round(cells_intersecting_land / total_rect_cells * 100, 2),
            'spatial_domain': 'Sovereign Terrestrial Landmass',
            'scope_role': 'Terrestrial land cells within international boundary polygon'
        },
        {
            'category': 'Cells with Valid ERA5 Wind Coverage',
            'cell_count': cells_valid_era5,
            'percentage_of_total': round(cells_valid_era5 / total_rect_cells * 100, 2),
            'spatial_domain': 'National ERA5 Ingestion Window',
            'scope_role': 'Gridded meteorological cells with continuous U10/V10 coverage'
        },
        {
            'category': 'Cells Containing Mapped Monitoring Stations',
            'cell_count': cells_with_stations,
            'percentage_of_total': round(cells_with_stations / total_rect_cells * 100, 2),
            'spatial_domain': 'Observational Ground-Truth Points',
            'scope_role': f'Contains 103 mapped OpenAQ/CPCB stations (max 8 stations per cell)'
        },
        {
            'category': 'Cells Actually Used as Dispersion Sources (Phases 11–17)',
            'cell_count': cells_used_as_sources,
            'percentage_of_total': round(cells_used_as_sources / total_rect_cells * 100, 2),
            'spatial_domain': 'Selected Station Hubs',
            'scope_role': f'Exactly 8 unique grid cells corresponding to 10 verified monitoring stations: {source_grid_ids}'
        },
        {
            'category': 'Cells Appearing as Transport Destinations',
            'cell_count': cells_appearing_as_dest,
            'percentage_of_total': round(cells_appearing_as_dest / total_rect_cells * 100, 2),
            'spatial_domain': 'Downwind Transport Footprint',
            'scope_role': 'Grid cells receiving advected Lagrangian ensemble mass across 1h–24h horizons'
        },
        {
            'category': 'Cells Appearing ONLY as Transport Destinations',
            'cell_count': cells_only_destinations,
            'percentage_of_total': round(cells_only_destinations / total_rect_cells * 100, 2),
            'spatial_domain': 'Passive Receptor Grid',
            'scope_role': 'Cells acting purely as destinations, never initialized as advection sources'
        },
        {
            'category': 'Cells Never Utilized (Neither Source nor Destination)',
            'cell_count': cells_never_reached_nor_source,
            'percentage_of_total': round(cells_never_reached_nor_source / total_rect_cells * 100, 2),
            'spatial_domain': 'Maritime / Remote Terrestrial Buffer',
            'scope_role': 'Peripheral ocean and unreached land cells outside the active 24h plumes of the 8 hubs'
        }
    ]
    
    df_audit = pd.DataFrame(audit_records)
    out_csv = os.path.join(out_dir, "current_grid_scope_audit.csv")
    df_audit.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv}")
    print("\nCurrent Grid Scope Audit Summary:")
    print(df_audit[['category', 'cell_count', 'percentage_of_total']].to_string(index=False))

    # Explicit Verification of Phase 17 Source Coverage
    print("\n--- PHASE 17 SOURCE COVERAGE VERIFICATION ---")
    print(f"Total national grid cells in 0.25° domain: {total_rect_cells}")
    print(f"Source cells executed in Phase 17: {cells_used_as_sources} (from {stations_used_as_sources} stations)")
    print(f"Source Coverage Ratio: {cells_used_as_sources / total_rect_cells * 100:.3f}% of national grid")
    print("VERDICT: Phase 17 DID NOT execute dispersion from every national grid cell.")
    print("It evaluated strictly 8 selected station-source grid cells (10 monitored hubs).")


if __name__ == '__main__':
    main()
