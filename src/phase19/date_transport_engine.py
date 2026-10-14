"""
Date-Specific Transport Engine for Phase 20 Interactive Queries
Phase 19 — Final Scientific Verification & Targeted Corrections

Provides an exact on-demand calculation path to evaluate date-specific 2D
pollution dispersion from any national 50 km grid cell or lat/lon coordinate:
- Accepts: Year, Month, Day, Latitude, Longitude (or Grid ID).
- Resolves source coordinates to 50 km cell in O(1) projected time.
- Uses the 4 actual available ERA5 synoptic time slices for that date:
  00:00, 06:00, 12:00, 18:00 UTC.
- Evaluates forward 24h dynamic trajectory integration (h = 1.0h) with
  spatially and temporally varying U10/V10 fields.
- Classifies destinations into the 4 explicit categories:
    1. Valid terrestrial 50 km land cell
    2. Internal non-terrestrial water/marine cell
    3. External domain exit into international waters/borders
    4. Unsupported meteorological coverage
- Averages across the 4 daily releases to produce the Date-Level Daily Footprint.
- Computes source-weighted influence index if source is a monitored cell.
- Explicitly flags is_ambient_aqi_prediction = False.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import netCDF4 as nc
import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from src.phase19.corrected_transport_adapter_50km import (
    Corrected50kmTransportAdapter,
    WINDOWS,
    N_ENSEMBLE,
    calculate_haversine_distance_km,
    ERA5_LAT_MIN,
    ERA5_LAT_MAX,
    ERA5_LON_MIN,
    ERA5_LON_MAX
)

class DateSpecificTransportEngine:
    def __init__(self, grid_csv="results/phase18_grid_audit/india_50km_grid.csv",
                 station_map_csv="results/phase18_grid_audit/station_to_50km_grid_mapping.csv",
                 monitored_stats_csv="results/phase19_transport/matrices/monitored_cells_concentration_summary.csv"):
        self.adapter = Corrected50kmTransportAdapter(grid_csv)
        self.df_st = pd.read_csv(station_map_csv) if os.path.exists(station_map_csv) else None
        self.monitored_stats = pd.read_csv(monitored_stats_csv) if os.path.exists(monitored_stats_csv) else None
        
        self.monitored_pm25_lookup = {}
        if self.monitored_stats is not None:
            self.monitored_pm25_lookup = dict(zip(
                self.monitored_stats['grid_id_50km'],
                self.monitored_stats['mean_observed_pm25_ugm3']
            ))

    def query_date_transport(self, year, month, day, lat=None, lon=None, grid_id=None, horizon_hours=24.0):
        """
        Calculates exact date-level transport footprint from a source location on a specific date.
        """
        # 1. Resolve source cell
        if grid_id is not None:
            if grid_id not in self.adapter.valid_cell_ids:
                raise ValueError(f"Invalid terrestrial grid ID: {grid_id}")
            src_gid = grid_id
            src_lat, src_lon = self.adapter.coords_lookup[src_gid]
        elif lat is not None and lon is not None:
            dest_arr = self.adapter.classify_positions([lon], [lat])
            src_gid = dest_arr[0]
            if not src_gid.startswith("IND_50KM"):
                return {
                    'status': 'ERROR_LOCATION_OUTSIDE_TERRESTRIAL_INDIA',
                    'message': f'Input coordinates ({lat:.4f}, {lon:.4f}) map to {src_gid}',
                    'results_table': pd.DataFrame()
                }
            src_lat, src_lon = self.adapter.coords_lookup[src_gid]
        else:
            raise ValueError("Must provide either grid_id or (lat, lon)")
            
        src_idx = np.where(self.adapter.cell_ids == src_gid)[0][0]
        
        # 2. Check ERA5 coverage
        if not self.adapter.source_is_supported[src_idx]:
            return {
                'status': 'UNSUPPORTED_MET_COVERAGE',
                'source_grid_id': src_gid,
                'source_latitude': src_lat,
                'source_longitude': src_lon,
                'message': f'Source cell {src_gid} lies outside ERA5 reanalysis domain bounds. Extrapolation prohibited.',
                'results_table': pd.DataFrame([{
                    'destination': 'UNSUPPORTED_MET_COVERAGE',
                    'transport_fraction': 1.0,
                    'note': 'ERA5 coverage unavailable for this cell'
                }])
            }
            
        # 3. Load ERA5 netCDF for the requested year
        nc_path = f"data/raw/era5/{year}/era5_{year}_instant.nc"
        if not os.path.exists(nc_path):
            raise FileNotFoundError(f"ERA5 reanalysis file missing for year {year}: {nc_path}")
            
        ds = nc.Dataset(nc_path)
        raw_lats = ds.variables['latitude'][:]
        raw_lons = ds.variables['longitude'][:]
        flip_lats = raw_lats[0] > raw_lats[-1]
        sorted_lats = raw_lats[::-1] if flip_lats else raw_lats
        
        vt = ds.variables['valid_time'][:]
        dt_times = pd.to_datetime(vt, unit='s', utc=True)
        
        # Target date string: YYYY-MM-DD
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        
        # Identify the 4 synoptic steps for this date: 00, 06, 12, 18 UTC
        synoptic_steps = np.where(
            (dt_times.year == year) &
            (dt_times.month == month) &
            (dt_times.day == day)
        )[0]
        
        if len(synoptic_steps) == 0:
            return {
                'status': 'ERROR_DATE_NOT_IN_DATASET',
                'message': f'Date {date_str} not found in ERA5 {year} dataset',
                'results_table': pd.DataFrame()
            }
            
        # 4. Integrate trajectories for each of the 4 releases
        # Each release integrates forward 24h (requires 5 slices: t0, t0+6h, t0+12h, t0+18h, t0+24h)
        daily_dests = []
        
        for r_idx, s_step in enumerate(synoptic_steps):
            u_slices = []
            v_slices = []
            valid_times = [0.0, 6.0, 12.0, 18.0, 24.0]
            
            for k in range(5):
                step_k = min(len(dt_times) - 1, s_step + k)
                u_k = ds.variables['u10'][step_k, :, :]
                v_k = ds.variables['v10'][step_k, :, :]
                u_sort = u_k[::-1, :] if flip_lats else u_k
                v_sort = v_k[::-1, :] if flip_lats else v_k
                
                iu = RegularGridInterpolator((sorted_lats, raw_lons), u_sort, bounds_error=False, fill_value=None)
                iv = RegularGridInterpolator((sorted_lats, raw_lons), v_sort, bounds_error=False, fill_value=None)
                u_slices.append(iu)
                v_slices.append(iv)
                
            horizon_res = self.adapter.integrate_trajectories(
                u_slices, v_slices, valid_times, synoptic_step_idx=s_step, dt_int_hours=1.0
            )
            # Extract destinations for the source cell at requested horizon
            dest_ensemble = horizon_res[horizon_hours][src_idx, :] # 10 members
            daily_dests.extend(dest_ensemble)
            
        # 5. Aggregate across the 4 releases (total 40 particles)
        total_particles = len(daily_dests)
        unique_d, counts = np.unique(daily_dests, return_counts=True)
        
        # Check source ground concentration
        has_ground_obs = src_gid in self.monitored_pm25_lookup
        src_pm25 = self.monitored_pm25_lookup.get(src_gid, np.nan)
        
        rows = []
        for d_id, c in zip(unique_d, counts):
            frac = c / float(total_particles)
            
            # Destination classification and distance
            if d_id.startswith("IND_50KM"):
                d_lat, d_lon = self.adapter.coords_lookup[d_id]
                dist_km = calculate_haversine_distance_km(src_lat, src_lon, d_lat, d_lon)
                category = "VALID_LAND_DESTINATION"
            elif d_id == "INTERNAL_UNMODELED_WATER":
                dist_km = np.nan
                category = "INTERNAL_UNMODELED_WATER"
            elif d_id == "DOMAIN_EXIT_EXTERNAL":
                dist_km = np.nan
                category = "DOMAIN_EXIT_EXTERNAL"
            else:
                dist_km = np.nan
                category = "UNSUPPORTED_MET_COVERAGE"
                
            # Modeled influence index
            if has_ground_obs and not np.isnan(src_pm25):
                inf_index = round(src_pm25 * frac, 4)
                inf_status = "CALCULATED_FROM_GROUND_TRUTH"
            else:
                inf_index = np.nan
                inf_status = "UNMONITORED_SOURCE_NO_INFLUENCE"
                
            rows.append({
                'destination': d_id,
                'category': category,
                'daily_transport_fraction': round(frac, 4),
                'particles_count': int(c),
                'total_daily_particles': total_particles,
                'distance_km': round(dist_km, 2) if not np.isnan(dist_km) else np.nan,
                'source_weighted_transport_influence_index': inf_index,
                'influence_status': inf_status,
                'is_ambient_aqi_prediction': False
            })
            
        df_out = pd.DataFrame(rows).sort_values(by='daily_transport_fraction', ascending=False).reset_index(drop=True)
        df_out['rank'] = df_out.index + 1
        
        return {
            'status': 'SUCCESS',
            'query_date': date_str,
            'source_grid_id': src_gid,
            'source_latitude': src_lat,
            'source_longitude': src_lon,
            'horizon_hours': horizon_hours,
            'synoptic_releases_count': len(synoptic_steps),
            'total_trajectories_evaluated': total_particles,
            'has_source_ground_observations': has_ground_obs,
            'source_climatological_pm25_ugm3': src_pm25,
            'scientific_disclaimer': 'Transport fractions represent physical 2D dispersion probability. Influence index represents dispersed source-tracer attribution metric in ug/m3-equivalent units. It is NOT measured ambient concentration and NOT destination AQI.',
            'results_table': df_out
        }


def test_date_engine():
    print("Testing DateSpecificTransportEngine on Delhi for 2021-10-15 (Post-Monsoon)...")
    engine = DateSpecificTransportEngine()
    query_res = engine.query_date_transport(
        year=2021, month=10, day=15,
        lat=28.6139, lon=77.2090, # Central Delhi
        horizon_hours=24.0
    )
    print(f"Status: {query_res['status']}")
    print(f"Source Cell: {query_res['source_grid_id']} (lat: {query_res['source_latitude']:.3f}, lon: {query_res['source_longitude']:.3f})")
    print(f"Query Date: {query_res['query_date']} across {query_res['synoptic_releases_count']} synoptic releases")
    print("\nTop 5 Destination Pathways at 24h Horizon:")
    df_top = query_res['results_table'].head(5)
    print(df_top[['rank', 'destination', 'category', 'daily_transport_fraction', 'distance_km', 'source_weighted_transport_influence_index']].to_string(index=False))

if __name__ == '__main__':
    test_date_engine()
