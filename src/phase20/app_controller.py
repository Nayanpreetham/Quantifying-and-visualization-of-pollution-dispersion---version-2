"""
App Controller for Phase 20 Interactive Application
Phase 20 - Interactive National Pollution Dispersion Query Application

Orchestrates user query handling, validation, coordinate-to-grid mapping,
date-specific transport calculations, caching, observation attribution,
and diagnostic synthesis.

Mandatory Constraints:
- 2D grid-to-grid historical transport calculation only.
- Strict input validation preventing out-of-bounds or invalid date execution.
- Deterministic reproducibility and composite caching (date + grid_id + horizon).
- Clear disaggregation of ground observations from modeled transport fractions.
- Explicit labeling: is_ambient_aqi_prediction = False.
"""

import os
import sys
import time
import datetime
import numpy as np
import pandas as pd

from src.phase19.date_transport_engine import DateSpecificTransportEngine
from src.phase19.corrected_transport_adapter_50km import calculate_haversine_distance_km
from src.phase20.observation_provider import ObservationProvider

SUPPORTED_YEAR_MIN = 2019
SUPPORTED_YEAR_MAX = 2024
SUPPORTED_HORIZONS = [1.0, 3.0, 6.0, 12.0, 24.0]


class AppController:
    def __init__(self,
                 grid_csv="results/phase18_grid_audit/india_50km_grid.csv",
                 station_map_csv="results/phase18_grid_audit/station_to_50km_grid_mapping.csv",
                 monitored_summary_csv="results/phase19_transport/matrices/monitored_cells_concentration_summary.csv"):
        self.engine = DateSpecificTransportEngine(
            grid_csv=grid_csv,
            station_map_csv=station_map_csv,
            monitored_stats_csv=monitored_summary_csv
        )
        self.obs_provider = ObservationProvider(
            station_map_csv=station_map_csv,
            monitored_summary_csv=monitored_summary_csv
        )
        self.cache = {}

    def validate_inputs(self, year, month, day, lat=None, lon=None, grid_id=None, horizon_hours=24.0):
        """
        Validates date, coordinates/grid_id, and horizon inputs before execution.
        
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        # 1. Date Validation
        try:
            query_date = datetime.date(int(year), int(month), int(day))
        except (ValueError, TypeError) as e:
            return False, f"Invalid calendar date: {year}-{month}-{day}. ({str(e)})"
            
        if query_date.year < SUPPORTED_YEAR_MIN or query_date.year > SUPPORTED_YEAR_MAX:
            return False, (
                f"Date {query_date} is outside the supported ERA5 reanalysis baseline period "
                f"({SUPPORTED_YEAR_MIN}-01-01 to {SUPPORTED_YEAR_MAX}-12-31)."
            )
            
        # 2. Horizon Validation
        try:
            h_val = float(horizon_hours)
            if h_val not in SUPPORTED_HORIZONS:
                return False, f"Unsupported transport horizon: {h_val}h. Must be one of {SUPPORTED_HORIZONS}."
        except (ValueError, TypeError):
            return False, f"Invalid horizon value: {horizon_hours}"
            
        # 3. Location Validation
        if grid_id is not None:
            if not isinstance(grid_id, str) or grid_id not in self.engine.adapter.valid_cell_ids:
                return False, f"Invalid or non-existent 50 km grid ID: '{grid_id}'."
        elif lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (ValueError, TypeError):
                return False, f"Coordinates must be numeric values. Received lat='{lat}', lon='{lon}'."
                
            # Quick geographical sanity check (India subcontinental box)
            if lat_f < 4.0 or lat_f > 40.0 or lon_f < 65.0 or lon_f > 100.0:
                return False, f"Coordinates ({lat_f:.4f}, {lon_f:.4f}) are far outside the Indian subcontinent."
        else:
            return False, "Must provide either (lat, lon) coordinates or a valid grid_id."
            
        return True, None

    def resolve_source_location(self, lat=None, lon=None, grid_id=None):
        """
        Resolves input coordinates or grid_id to the 50 km national grid cell,
        calculating geographic offsets and monitoring metadata.
        
        Returns:
            dict: Source cell resolution metadata or error dict.
        """
        if grid_id is not None:
            src_gid = grid_id
            src_lat, src_lon = self.engine.adapter.coords_lookup[src_gid]
            user_lat, user_lon = src_lat, src_lon
            offset_km = 0.0
        else:
            user_lat = float(lat)
            user_lon = float(lon)
            dest_arr = self.engine.adapter.classify_positions([user_lon], [user_lat])
            src_gid = dest_arr[0]
            
            if src_gid == "INTERNAL_UNMODELED_WATER":
                return {
                    'status': 'ERROR_LOCATION_IN_WATER',
                    'message': f"Coordinates ({user_lat:.4f}, {user_lon:.4f}) fall in internal non-terrestrial coastal/marine waters."
                }
            elif src_gid == "DOMAIN_EXIT_EXTERNAL":
                return {
                    'status': 'ERROR_LOCATION_OUTSIDE_GRID',
                    'message': f"Coordinates ({user_lat:.4f}, {user_lon:.4f}) lie outside the national 50 km grid matrix envelope."
                }
            elif src_gid == "UNSUPPORTED_MET_COVERAGE":
                return {
                    'status': 'ERROR_UNSUPPORTED_MET_COVERAGE',
                    'message': f"Coordinates ({user_lat:.4f}, {user_lon:.4f}) lie outside the ERA5 reanalysis coordinate box [6N-35N, 68E-97E]."
                }
            
            src_lat, src_lon = self.engine.adapter.coords_lookup[src_gid]
            offset_km = calculate_haversine_distance_km(user_lat, user_lon, src_lat, src_lon)

        src_idx = np.where(self.engine.adapter.cell_ids == src_gid)[0][0]
        is_met_supported = bool(self.engine.adapter.source_is_supported[src_idx])
        
        # Check monitoring metadata
        row_num = int(self.engine.adapter.grid_df.loc[src_idx, 'row'])
        col_num = int(self.engine.adapter.grid_df.loc[src_idx, 'column'])
        land_frac = float(self.engine.adapter.grid_df.loc[src_idx, 'land_fraction'])
        
        return {
            'status': 'SUCCESS',
            'grid_id_50km': src_gid,
            'source_latitude': src_lat,
            'source_longitude': src_lon,
            'user_latitude': user_lat,
            'user_longitude': user_lon,
            'offset_to_centroid_km': round(offset_km, 2),
            'row': row_num,
            'column': col_num,
            'land_fraction': land_frac,
            'is_meteorology_supported': is_met_supported
        }

    def execute_query(self, year, month, day, lat=None, lon=None, grid_id=None, horizon_hours=24.0, use_cache=True):
        """
        Executes a date-specific dispersion query with end-to-end integration:
        - Input validation.
        - Source cell resolution.
        - ERA5 dynamic Lagrangian trajectory simulation across the 4 daily synoptic releases.
        - Observation lookup for ground PM2.5 and date-matched regional AQI ranking.
        - Diagnostic profiling.
        """
        t_start = time.time()
        
        # 1. Validate inputs
        is_valid, err_msg = self.validate_inputs(year, month, day, lat, lon, grid_id, horizon_hours)
        if not is_valid:
            return {
                'status': 'VALIDATION_ERROR',
                'message': err_msg,
                'results_table': pd.DataFrame()
            }
            
        # 2. Resolve source location
        res_loc = self.resolve_source_location(lat=lat, lon=lon, grid_id=grid_id)
        if res_loc['status'] != 'SUCCESS':
            return {
                'status': res_loc['status'],
                'message': res_loc['message'],
                'results_table': pd.DataFrame()
            }
            
        src_gid = res_loc['grid_id_50km']
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        h_val = float(horizon_hours)
        
        # Check meteorological coverage
        if not res_loc['is_meteorology_supported']:
            df_unsupp = pd.DataFrame([{
                'rank': 1,
                'source_grid_id': src_gid,
                'destination': 'UNSUPPORTED_MET_COVERAGE',
                'source_latitude': res_loc['source_latitude'],
                'source_longitude': res_loc['source_longitude'],
                'dest_latitude': np.nan,
                'dest_longitude': np.nan,
                'category': 'UNSUPPORTED_MET_COVERAGE',
                'daily_transport_fraction': 1.0,
                'particles_count': 40,
                'total_daily_particles': 40,
                'distance_km': np.nan,
                'source_weighted_transport_influence_index': np.nan,
                'influence_status': 'UNSUPPORTED_MET_COVERAGE',
                'is_ambient_aqi_prediction': False
            }])
            return {
                'status': 'UNSUPPORTED_MET_COVERAGE',
                'query_date': date_str,
                'source_info': res_loc,
                'message': (
                    f"Source cell {src_gid} lies outside the ERA5 reanalysis coverage bounds "
                    "[6N-35N, 68E-97E]. Silent extrapolation is prohibited by project methodology."
                ),
                'results_table': df_unsupp,
                'execution_time_seconds': round(time.time() - t_start, 3),
                'cache_hit': False
            }
            
        # 3. Check Cache
        cache_key = (int(year), int(month), int(day), src_gid, h_val)
        cache_hit = False
        
        if use_cache and cache_key in self.cache:
            raw_engine_res = self.cache[cache_key]
            cache_hit = True
        else:
            # 4. Execute Engine
            raw_engine_res = self.engine.query_date_transport(
                year=int(year),
                month=int(month),
                day=int(day),
                grid_id=src_gid,
                horizon_hours=h_val
            )
            if use_cache and raw_engine_res['status'] == 'SUCCESS':
                self.cache[cache_key] = raw_engine_res

        if raw_engine_res['status'] != 'SUCCESS':
            return {
                'status': raw_engine_res['status'],
                'message': raw_engine_res.get('message', 'Engine query failed.'),
                'results_table': pd.DataFrame()
            }

        # 5. Get Ground Observation Status for Source Cell
        mon_info = self.obs_provider.get_source_cell_monitoring_info(src_gid, date_str)
        effective_source_pm25 = mon_info['effective_source_pm25_ugm3']
        
        # 6. Build Final Table with standard schema
        df_engine = raw_engine_res['results_table'].copy()
        
        # Add source and destination coordinates
        df_engine['source_grid_id'] = src_gid
        df_engine['source_latitude'] = res_loc['source_latitude']
        df_engine['source_longitude'] = res_loc['source_longitude']
        
        dest_lats = []
        dest_lons = []
        for d in df_engine['destination']:
            if d.startswith("IND_50KM"):
                coords = self.engine.adapter.coords_lookup.get(d)
                dest_lats.append(coords[0] if coords else np.nan)
                dest_lons.append(coords[1] if coords else np.nan)
            else:
                dest_lats.append(np.nan)
                dest_lons.append(np.nan)
        df_engine['dest_latitude'] = dest_lats
        df_engine['dest_longitude'] = dest_lons
        
        # Recompute source-weighted influence index based on precise observation status
        if not np.isnan(effective_source_pm25):
            df_engine['source_weighted_transport_influence_index'] = (
                df_engine['daily_transport_fraction'] * effective_source_pm25
            ).round(4)
            df_engine['influence_status'] = mon_info['monitoring_status']
        else:
            df_engine['source_weighted_transport_influence_index'] = np.nan
            df_engine['influence_status'] = "UNMONITORED_SOURCE_NO_INFLUENCE"
            
        df_engine['is_ambient_aqi_prediction'] = False
        
        # Reorder columns
        col_order = [
            'rank', 'source_grid_id', 'destination', 'category',
            'daily_transport_fraction', 'particles_count', 'total_daily_particles',
            'distance_km', 'source_weighted_transport_influence_index',
            'influence_status', 'source_latitude', 'source_longitude',
            'dest_latitude', 'dest_longitude', 'is_ambient_aqi_prediction'
        ]
        df_engine = df_engine[col_order]
        
        # 7. Retrieve Date-Matched Regional Rankings
        cpcb_rankings = self.obs_provider.get_cpcb_aqi_ranking(date_str)
        openaq_rankings = self.obs_provider.get_openaq_pm25_ranking(date_str)
        
        t_elapsed = round(time.time() - t_start, 3)
        
        # Diagnostics
        cat_counts = df_engine['category'].value_counts().to_dict()
        closure_sum = round(float(df_engine['daily_transport_fraction'].sum()), 6)
        
        return {
            'status': 'SUCCESS',
            'query_date': date_str,
            'horizon_hours': h_val,
            'source_info': res_loc,
            'monitoring_info': mon_info,
            'synoptic_releases': ['00:00 UTC', '06:00 UTC', '12:00 UTC', '18:00 UTC'],
            'total_ensemble_particles': int(df_engine['total_daily_particles'].iloc[0]),
            'probability_closure_sum': closure_sum,
            'category_counts': cat_counts,
            'execution_time_seconds': t_elapsed,
            'cache_hit': cache_hit,
            'results_table': df_engine,
            'date_matched_cpcb_ranking': cpcb_rankings,
            'date_matched_openaq_ranking': openaq_rankings,
            'scientific_disclaimer': (
                "Scientific Integrity Notice: "
                "1. Transport fractions represent physical 2D dispersion probability across the 50 km grid.\n"
                "2. Source-weighted influence index represents dispersed source-tracer attribution (ug/m3-equiv) and is NOT destination ambient AQI.\n"
                "3. Ground observations (CPCB/OpenAQ) are independent empirical measurements presented for regional context and are NOT model outputs."
            )
        }
