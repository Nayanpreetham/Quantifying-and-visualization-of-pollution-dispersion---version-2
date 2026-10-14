"""
Task 2: Construct a True 50 km x 50 km National Grid for India
Phase 18 — National 50 km x 50 km Grid Design and Coverage Audit

Constructs square 50 km x 50 km cells in EPSG:7755 (Survey of India Lambert Conformal Conic).
Calculates exact land intersection areas, land-area fractions, cell centers, and boundary flags.
Saves:
- results/phase18_grid_audit/india_50km_grid.geojson
- results/phase18_grid_audit/india_50km_grid.csv
"""

import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box, mapping

GRID_STEP_M = 50000.0  # 50,000 metres (50 km)
PROJ_CRS = "EPSG:7755" # WGS 84 / India NSF LCC

def main():
    print("=== Phase 18 Task 2: Construct True 50 km x 50 km National Grid ===")
    out_dir = "results/phase18_grid_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Load Sovereign Land Boundary
    land_path = "data/raw/geography/india_land_boundary.geojson"
    gdf_land = gpd.read_file(land_path).to_crs(PROJ_CRS)
    india_geom = gdf_land.geometry.iloc[0]
    total_land_area_sqkm = gdf_land.geometry.area.sum() / 1e6
    print(f"Loaded Sovereign Land Boundary: {total_land_area_sqkm:,.2f} sq km")
    
    # 2. Establish Grid Origin and Aligned Bounds
    minx, miny, maxx, maxy = gdf_land.total_bounds
    x_min = np.floor(minx / GRID_STEP_M) * GRID_STEP_M
    y_min = np.floor(miny / GRID_STEP_M) * GRID_STEP_M
    x_max = np.ceil(maxx / GRID_STEP_M) * GRID_STEP_M
    y_max = np.ceil(maxy / GRID_STEP_M) * GRID_STEP_M
    
    x_coords = np.arange(x_min, x_max, GRID_STEP_M)
    y_coords = np.arange(y_min, y_max, GRID_STEP_M)
    n_cols = len(x_coords)
    n_rows = len(y_coords)
    total_domain_rect_cells = n_rows * n_cols
    print(f"Projected Extent (EPSG:7755): X [{x_min:,.0f}, {x_max:,.0f}] ({n_cols} cols), Y [{y_min:,.0f}, {y_max:,.0f}] ({n_rows} rows)")
    print(f"Total rectangular cells in national bounding box: {total_domain_rect_cells}")
    
    # 3. Construct Cells and Intersect with Landmass
    cells_list = []
    cell_polygons = []
    
    nominal_cell_area_km2 = (GRID_STEP_M * GRID_STEP_M) / 1e6 # 2,500 sq km
    
    for r_idx, y in enumerate(y_coords):
        for c_idx, x in enumerate(x_coords):
            cell_poly = box(x, y, x + GRID_STEP_M, y + GRID_STEP_M)
            if cell_poly.intersects(india_geom):
                inter = cell_poly.intersection(india_geom)
                land_area_km2 = inter.area / 1e6
                land_fraction = float(land_area_km2 / nominal_cell_area_km2)
                
                # Classify boundary / retention status
                if land_fraction >= 0.999:
                    retention_flag = "CORE_INTERIOR"
                    is_boundary = False
                elif land_fraction >= 0.50:
                    retention_flag = "MAJORITY_LAND"
                    is_boundary = True
                elif land_fraction >= 0.10:
                    retention_flag = "COASTAL_BORDER_SIGNIFICANT"
                    is_boundary = True
                else:
                    retention_flag = "COASTAL_BORDER_SLIGHT"
                    is_boundary = True
                    
                grid_id = f"IND_50KM_r{r_idx:03d}_c{c_idx:03d}"
                
                cells_list.append({
                    'grid_id_50km': grid_id,
                    'row': r_idx,
                    'column': c_idx,
                    'nominal_side_length_m': GRID_STEP_M,
                    'nominal_area_km2': nominal_cell_area_km2,
                    'x_min_m': x,
                    'y_min_m': y,
                    'x_max_m': x + GRID_STEP_M,
                    'y_max_m': y + GRID_STEP_M,
                    'x_center_m': x + GRID_STEP_M / 2.0,
                    'y_center_m': y + GRID_STEP_M / 2.0,
                    'land_area_km2': round(land_area_km2, 2),
                    'land_fraction': round(land_fraction, 4),
                    'is_boundary_cell': is_boundary,
                    'retention_policy': retention_flag,
                    'crs_identifier': PROJ_CRS
                })
                cell_polygons.append(cell_poly)
                
    gdf_50km = gpd.GeoDataFrame(cells_list, geometry=cell_polygons, crs=PROJ_CRS)
    print(f"Total cells intersecting land: {len(gdf_50km)}")
    
    # 4. Compute Unprojected WGS84 Geographic Coordinates (Center and Bounding Box)
    gdf_wgs84 = gdf_50km.to_crs("EPSG:4326")
    centroids_wgs84 = gdf_50km.geometry.centroid.to_crs("EPSG:4326")
    
    gdf_50km['center_longitude_deg'] = centroids_wgs84.x.round(6)
    gdf_50km['center_latitude_deg'] = centroids_wgs84.y.round(6)
    
    bounds_wgs84 = gdf_wgs84.bounds
    gdf_50km['lon_min_deg'] = bounds_wgs84['minx'].round(6)
    gdf_50km['lat_min_deg'] = bounds_wgs84['miny'].round(6)
    gdf_50km['lon_max_deg'] = bounds_wgs84['maxx'].round(6)
    gdf_50km['lat_max_deg'] = bounds_wgs84['maxy'].round(6)
    
    # Sort logically by row then column
    gdf_50km = gdf_50km.sort_values(by=['row', 'column']).reset_index(drop=True)
    
    # 5. Save GeoJSON (in WGS84 EPSG:4326 for universal GIS standard)
    out_geojson = os.path.join(out_dir, "india_50km_grid.geojson")
    gdf_wgs84_out = gdf_50km.to_crs("EPSG:4326")
    gdf_wgs84_out.to_file(out_geojson, driver="GeoJSON")
    print(f"Saved: {out_geojson} ({len(gdf_50km)} features)")
    
    # 6. Save CSV
    out_csv = os.path.join(out_dir, "india_50km_grid.csv")
    df_csv = gdf_50km.drop(columns=['geometry'])
    df_csv.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv} ({len(df_csv)} rows)")
    
    # Summary by Retention Policy
    print("\n50 km Grid Breakdown by Boundary / Retention Policy:")
    print(df_csv['retention_policy'].value_counts())
    print(f"\nTotal Land Area Accounted: {df_csv['land_area_km2'].sum():,.2f} sq km")
    print(f"Total Represented Grid Footprint: {len(df_csv) * nominal_cell_area_km2:,.2f} sq km")


if __name__ == '__main__':
    main()
