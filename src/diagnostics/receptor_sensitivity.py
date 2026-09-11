import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
import os
import math
from src.physics.kljun import kljun_ffp
from shapely.geometry import Point
import warnings
warnings.filterwarnings('ignore')

GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
TIMESTAMP = '2020-11-01 12:00:00'

grid = gpd.read_file(GRID_FILE)
ds = xr.open_dataset(ERA5_DATA).sel(valid_time=pd.to_datetime(TIMESTAMP))

india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
grid_metric = grid.to_crs(india_crs)

TARGETS = {
    'Delhi': 'IND_047_021',
    'Mumbai': 'IND_026_012',
    'Varanasi': 'IND_040_032'
}
HEIGHTS = [10.0, 25.0, 50.0, 100.0, 200.0]

results = []
report = ["# Receptor Height Sensitivity & Scale Mismatch Analysis\n"]

for city, gid in TARGETS.items():
    print(f"\nProcessing {city} ({gid})...")
    report.append(f"## {city}\n")
    
    target_row = grid_metric[grid_metric['grid_id'] == gid].iloc[0]
    cx_t = target_row.geometry.centroid.x
    cy_t = target_row.geometry.centroid.y
    cx_deg = target_row['center_lon']
    cy_deg = target_row['center_lat']
    
    m = ds.sel(longitude=cx_deg, latitude=cy_deg, method='nearest')
    wd = float(m['wind_direction'].values)
    ws = float(m['wind_speed'].values)
    u_star = float(m['u_star'].values)
    L = float(m['L'].values)
    sigma_v = float(m['sigma_v'].values)
    blh = float(m['pblh'].values)
    
    wd_rad = math.radians((90 - wd) % 360)
    cos_wd = math.cos(wd_rad)
    sin_wd = math.sin(wd_rad)
    
    # We use a 300km x 300km box with 500m resolution to handle higher heights
    max_dist = 150000.0
    res = 500.0
    
    xs = np.arange(-max_dist, max_dist, res)
    ys = np.arange(-max_dist, max_dist, res)
    xx, yy = np.meshgrid(xs, ys)
    
    grid_x = cx_t + xx
    grid_y = cy_t + yy
    
    x_rot = xx * cos_wd + yy * sin_wd
    y_rot = -xx * sin_wd + yy * cos_wd
    
    for zm in HEIGHTS:
        print(f"  Height: {zm}m")
        f, flag = kljun_ffp(zm, 0.1, ws, blh, L, sigma_v, u_star, x_rot, y_rot)
        f[np.isnan(f)] = 0
        f[f < 0] = 0
        
        # Calculate upwind cumulative distances
        # Sum along crosswind (y_rot). Since our mesh is regular but rotated, 
        # it's better to sort points by their upwind distance x_rot.
        x_rot_flat = x_rot.flatten()
        f_flat = f.flatten()
        
        valid = f_flat > 1e-12
        x_valid = x_rot_flat[valid]
        f_valid = f_flat[valid]
        
        if len(x_valid) == 0:
            print("    Zero footprint mass generated.")
            continue
            
        sort_idx = np.argsort(x_valid)
        x_sorted = x_valid[sort_idx]
        f_sorted = f_valid[sort_idx]
        
        cum_f = np.cumsum(f_sorted) * (res * res)
        total_mass = cum_f[-1]
        
        cum_pct = cum_f / total_mass
        
        d50 = x_sorted[np.argmax(cum_pct >= 0.5)] / 1000.0 if np.any(cum_pct >= 0.5) else 0
        d80 = x_sorted[np.argmax(cum_pct >= 0.8)] / 1000.0 if np.any(cum_pct >= 0.8) else 0
        d90 = x_sorted[np.argmax(cum_pct >= 0.9)] / 1000.0 if np.any(cum_pct >= 0.9) else 0
        
        # Footprint area (Area containing 80% of mass)
        # Sort by density (highest first) to find smallest area containing 80% mass
        f_density_sort = np.sort(f_valid)[::-1]
        cum_density_mass = np.cumsum(f_density_sort) * (res * res)
        idx_80 = np.argmax(cum_density_mass >= (0.8 * total_mass))
        area_80_km2 = (idx_80 + 1) * (res * res) / 1000000.0
        
        # Intersection with grids
        pts = gpd.points_from_xy(grid_x.flatten()[valid], grid_y.flatten()[valid], crs=india_crs)
        fp_gdf = gpd.GeoDataFrame({'f_density': f_valid}, geometry=pts, crs=india_crs)
        
        xmin, ymin, xmax, ymax = fp_gdf.total_bounds
        nearby_grids = grid_metric.cx[xmin:xmax, ymin:ymax]
        
        joined = gpd.sjoin(fp_gdf, nearby_grids[['grid_id', 'geometry']], how='left', predicate='within')
        joined['mass'] = joined['f_density'] * (res * res)
        
        inside = joined.dropna(subset=['grid_id'])
        mass_inside = inside['mass'].sum()
        mass_outside = joined[joined['grid_id'].isna()]['mass'].sum()
        
        pct_in = (mass_inside / total_mass) * 100
        pct_out = (mass_outside / total_mass) * 100
        
        sources = inside.groupby('grid_id')['mass'].sum().reset_index()
        sources['weight_pct'] = (sources['mass'] / mass_inside) * 100 if mass_inside > 0 else 0
        sources = sources.sort_values('weight_pct', ascending=False)
        
        # Number of meaningful grids (> 1% contribution)
        meaningful_grids = (sources['weight_pct'] > 1.0).sum()
        
        report.append(f"### Z_m = {zm} m")
        report.append(f"- **Footprint Distances**: 50% = {d50:.1f} km, 80% = {d80:.1f} km, 90% = {d90:.1f} km")
        report.append(f"- **80% Footprint Area**: {area_80_km2:.2f} km²")
        report.append(f"- **Total Grids hit**: {len(sources)} | **Meaningful Grids (>1%)**: {meaningful_grids}")
        report.append(f"- **Domain Coverage**: {pct_in:.1f}% Inside India, {pct_out:.1f}% Outside")
        report.append("- **Top Sources:**")
        
        for _, s in sources.head(10).iterrows():
            if s['weight_pct'] > 0.1:
                sgid = s['grid_id']
                dist = target_row.geometry.centroid.distance(nearby_grids.set_index('grid_id').loc[sgid, 'geometry'].centroid) / 1000.0
                report.append(f"  - **{sgid}**: {s['weight_pct']:.1f}% (Distance to center: {dist:.1f} km)")
                
        report.append("")

report.append("## Conclusion on Scale Mismatch")
report.append("Based on the physics above, if the footprint remains concentrated within the local 50-km cell even at elevated receptor heights (e.g. 50-100m), Kljun is physically incapable of resolving inter-cell transport on a 50x50 km grid. Recommending alternative approaches in this document.")

with open('docs/kljun_scale_mismatch_report.md', 'w') as f:
    f.write("\n".join(report))

print("Saved report to docs/kljun_scale_mismatch_report.md")
