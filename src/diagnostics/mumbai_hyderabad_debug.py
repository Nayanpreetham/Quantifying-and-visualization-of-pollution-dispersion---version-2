import xarray as xr
import geopandas as gpd
import pandas as pd
import numpy as np
import math
from src.physics.kljun import kljun_ffp
from shapely.geometry import Point

GRID_FILE = 'data/processed/grid/india_50km_grid.geojson'
ERA5_DATA = 'data/processed/era5/era5_2020_11.nc'
TIMESTAMP = '2020-11-01 12:00:00'

grid = gpd.read_file(GRID_FILE)
ds = xr.open_dataset(ERA5_DATA).sel(valid_time=pd.to_datetime(TIMESTAMP))

india_crs = '+proj=aea +lat_1=12 +lat_2=28 +lat_0=24 +lon_0=80 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
grid_metric = grid.to_crs(india_crs)

TARGETS = {
    'Mumbai': 'IND_026_012',
    'Hyderabad': 'IND_022_023'
}

for city, gid in TARGETS.items():
    print(f"\n{'='*50}\nDEBUGGING {city} ({gid})\n{'='*50}")
    target_row = grid_metric[grid_metric['grid_id'] == gid].iloc[0]
    
    cx_t = target_row.geometry.centroid.x
    cy_t = target_row.geometry.centroid.y
    cx_deg = target_row['center_lon']
    cy_deg = target_row['center_lat']
    
    print(f"Target Centroid (Deg): {cy_deg:.2f}N, {cx_deg:.2f}E")
    
    m = ds.sel(longitude=cx_deg, latitude=cy_deg, method='nearest')
    wd = float(m['wind_direction'].values)
    ws = float(m['wind_speed'].values)
    print(f"Meteorology: Wind Speed = {ws:.2f} m/s, Wind Direction = {wd:.1f} deg")
    
    wd_rad = math.radians((90 - wd) % 360)
    print(f"Mathematical Angle used for Kljun X-axis: {math.degrees(wd_rad):.1f} deg")
    
    res = 1000.0
    max_dist = 50000.0 # 50km
    
    xs = np.arange(-max_dist, max_dist, res)
    ys = np.arange(-max_dist, max_dist, res)
    xx, yy = np.meshgrid(xs, ys)
    
    grid_x = cx_t + xx
    grid_y = cy_t + yy
    
    x_rot = xx * math.cos(wd_rad) + yy * math.sin(wd_rad)
    y_rot = -xx * math.sin(wd_rad) + yy * math.cos(wd_rad)
    
    f, _ = kljun_ffp(10.0, 0.1, ws, float(m['pblh']), float(m['L']), float(m['sigma_v']), float(m['u_star']), x_rot, y_rot)
    
    idx_max = np.nanargmax(f)
    xmax, ymax = xx.flatten()[idx_max], yy.flatten()[idx_max]
    
    print(f"Footprint Max (relative to target): dx = {xmax} m, dy = {ymax} m")
    
    bearing_rad = math.atan2(ymax, xmax)
    bearing_deg = (math.degrees(bearing_rad) + 360) % 360
    
    math_bearing = bearing_deg
    geo_bearing = (90 - math_bearing + 360) % 360
    print(f"Geographic Bearing of footprint MAX (0=N, 90=E): {geo_bearing:.1f} deg")
    print(f"Wind coming FROM (ERA5 convention): {wd:.1f} deg")
    
    if abs(geo_bearing - wd) > 10 and abs(geo_bearing - wd) < 350:
        print(">>> ALERT: Wind direction and footprint upwind direction DO NOT MATCH! Rotation is wrong.")
    else:
        print(">>> Footprint is correctly pointing UPWIND.")
