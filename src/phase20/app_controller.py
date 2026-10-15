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
        self.matrix_cache = {}

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

    def load_transport_matrix(self, year, month, day=None):
        """
        Loads the precomputed national transport matrix for the specified date/month.
        If date is 2021-10-15 (Pilot Run), loads the high-resolution single-day corrected matrix.
        Otherwise, loads the monthly transport matrix from results/phase19_transport/monthly/.
        Returns (df_matrix, matrix_source_name).
        """
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}" if day is not None else None
        
        # Check pilot matrix for 2021-10-15
        if date_str == "2021-10-15":
            pilot_path = "results/phase19_transport/correction_audit/pilot/transport_matrix_pilot_corrected_50km.csv"
            if os.path.exists(pilot_path):
                cache_key = ("pilot", 2021, 10, 15)
                if cache_key not in self.matrix_cache:
                    self.matrix_cache[cache_key] = pd.read_csv(pilot_path)
                return self.matrix_cache[cache_key], "Pilot Day Matrix (2021-10-15 Corrected)"
                
        # Monthly matrix
        cache_key = ("monthly", int(year), int(month))
        if cache_key in self.matrix_cache:
            return self.matrix_cache[cache_key], f"Monthly Transport Matrix ({int(year):04d}-{int(month):02d})"
            
        month_path = f"results/phase19_transport/monthly/transport_matrix_50km_{int(year):04d}_{int(month):02d}.parquet"
        if os.path.exists(month_path):
            df_m = pd.read_parquet(month_path)
            self.matrix_cache[cache_key] = df_m
            return df_m, f"Monthly Transport Matrix ({int(year):04d}-{int(month):02d})"
            
        # Fallback to multi-year baseline matrix
        baseline_path = "results/phase19_transport/matrices/modeled_influence_50km_baseline.parquet"
        if os.path.exists(baseline_path):
            cache_key = ("baseline",)
            if cache_key not in self.matrix_cache:
                self.matrix_cache[cache_key] = pd.read_parquet(baseline_path)
            return self.matrix_cache[cache_key], "Multi-Year Baseline Matrix (2019-2024)"
            
        raise FileNotFoundError(f"No transport matrix found for year {year}, month {month}.")

    def execute_target_query(self, year, month, day, lat=None, lon=None, grid_id=None, horizon_hours=24.0, ranking_metric='transport_fraction', use_cache=True):
        """
        Executes a target-centric pollution influence query.
        Given a target location anywhere in India:
        - Resolves target coordinates to the 50 km national grid.
        - Identifies eligible candidate source cells across India whose forward modeled transport reaches this target cell.
        - Extracts the modeled transport fraction T_{ij}(date, horizon).
        - Computes the source-weighted influence index I_{ij} = C_i * T_{ij} if ground observation C_i is available at source i.
        - Strictly marks unmonitored source cells with NaN influence index.
        - Ranks incoming candidate sources by transport_fraction or source_weighted_transport_influence_index.
        - Explicitly flags is_ambient_aqi_prediction = False.
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
            
        # 2. Resolve target location
        res_loc = self.resolve_source_location(lat=lat, lon=lon, grid_id=grid_id)
        if res_loc['status'] != 'SUCCESS':
            return {
                'status': res_loc['status'],
                'message': res_loc['message'],
                'results_table': pd.DataFrame()
            }
            
        target_gid = res_loc['grid_id_50km']
        target_lat = res_loc['source_latitude']
        target_lon = res_loc['source_longitude']
        user_lat = res_loc['user_latitude']
        user_lon = res_loc['user_longitude']
        offset_km = res_loc['offset_to_centroid_km']
        date_str = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
        h_val = float(horizon_hours)
        
        # Check meteorological coverage for target
        if not res_loc['is_meteorology_supported']:
            df_unsupp = pd.DataFrame([{
                'rank': 1,
                'target_grid_id': target_gid,
                'target_latitude': target_lat,
                'target_longitude': target_lon,
                'source_grid_id': 'UNSUPPORTED_MET_COVERAGE',
                'source_latitude': np.nan,
                'source_longitude': np.nan,
                'distance_km': np.nan,
                'daily_transport_fraction': np.nan,
                'particles_count': 0,
                'total_particles': 0,
                'source_pm25_ugm3': np.nan,
                'source_weighted_transport_influence_index': np.nan,
                'source_observation_status': 'UNSUPPORTED_MET_COVERAGE',
                'influence_status': 'UNSUPPORTED_MET_COVERAGE',
                'query_date': date_str,
                'horizon_hours': h_val,
                'is_ambient_aqi_prediction': False
            }])
            return {
                'status': 'UNSUPPORTED_MET_COVERAGE',
                'query_type': 'TARGET_INFLUENCE',
                'query_date': date_str,
                'horizon_hours': h_val,
                'target_info': res_loc,
                'message': (
                    f"Target cell {target_gid} lies outside the ERA5 reanalysis coverage bounds "
                    "[6N-35N, 68E-97E]. Silent extrapolation is prohibited by project methodology."
                ),
                'results_table': df_unsupp,
                'execution_time_seconds': round(time.time() - t_start, 3),
                'cache_hit': False
            }
            
        # 3. Check Cache
        cache_key = ('target', int(year), int(month), int(day), target_gid, h_val, ranking_metric)
        if use_cache and cache_key in self.cache:
            res_cached = dict(self.cache[cache_key])
            res_cached['cache_hit'] = True
            res_cached['execution_time_seconds'] = round(time.time() - t_start, 3)
            return res_cached

        # 4. Load Transport Matrix
        try:
            df_mat, mat_source = self.load_transport_matrix(year, month, day)
        except Exception as e:
            return {
                'status': 'DATA_LOADING_ERROR',
                'message': f"Failed to load transport matrix for {date_str}: {str(e)}",
                'results_table': pd.DataFrame()
            }
            
        # 5. Filter for target cell as destination
        mask = (df_mat['dest_grid_id'] == target_gid) & (df_mat['elapsed_time_hours'] == h_val)
        df_target_match = df_mat[mask].copy()
        
        target_info = {
            'target_grid_id': target_gid,
            'target_latitude': target_lat,
            'target_longitude': target_lon,
            'user_latitude': user_lat,
            'user_longitude': user_lon,
            'offset_to_centroid_km': offset_km,
            'row': res_loc['row'],
            'column': res_loc['column'],
            'land_fraction': res_loc['land_fraction'],
            'is_meteorology_supported': res_loc['is_meteorology_supported']
        }
        
        target_mon_info = self.obs_provider.get_source_cell_monitoring_info(target_gid, date_str)
        
        if df_target_match.empty:
            df_empty = pd.DataFrame(columns=[
                'rank', 'target_grid_id', 'target_latitude', 'target_longitude',
                'source_grid_id', 'source_latitude', 'source_longitude',
                'distance_km', 'daily_transport_fraction', 'particles_count',
                'total_particles', 'source_pm25_ugm3',
                'source_weighted_transport_influence_index',
                'source_observation_status', 'influence_status',
                'query_date', 'horizon_hours', 'is_ambient_aqi_prediction'
            ])
            return {
                'status': 'SUCCESS',
                'query_type': 'TARGET_INFLUENCE',
                'query_date': date_str,
                'horizon_hours': h_val,
                'target_info': target_info,
                'target_monitoring_info': target_mon_info,
                'ranking_metric': ranking_metric,
                'total_candidate_sources': 1380,
                'sources_with_positive_transport': 0,
                'monitored_sources_count': 0,
                'unmonitored_sources_count': 0,
                'results_table': df_empty,
                'execution_time_seconds': round(time.time() - t_start, 3),
                'cache_hit': False,
                'matrix_source': mat_source,
                'scientific_disclaimer': (
                    "Scientific Integrity Notice: No modeled forward transport pathways reached this target cell "
                    f"for horizon {h_val:g}h on {date_str}."
                )
            }
            
        # 6. Build Result Records
        records = []
        monitored_count = 0
        unmonitored_count = 0
        
        for _, row in df_target_match.iterrows():
            src_id = str(row['source_grid_id'])
            frac = round(float(row['mean_transport_fraction']), 6)
            
            # Lookup source coordinates
            src_coords = self.engine.adapter.coords_lookup.get(src_id)
            if src_coords:
                s_lat, s_lon = src_coords
            else:
                s_lat, s_lon = np.nan, np.nan
                
            # Distance
            if 'distance_km' in row and not pd.isna(row['distance_km']):
                dist_km = round(float(row['distance_km']), 1)
            elif not np.isnan(s_lat):
                dist_km = round(calculate_haversine_distance_km(target_lat, target_lon, s_lat, s_lon), 1)
            else:
                dist_km = np.nan
                
            p_count = int(row.get('transported_particles_count', 0))
            tot_p = int(row.get('total_possible_particles', 0))
            
            # Lookup source observation
            src_mon = self.obs_provider.get_source_cell_monitoring_info(src_id, date_str)
            src_pm25 = src_mon['effective_source_pm25_ugm3']
            
            if not np.isnan(src_pm25):
                monitored_count += 1
                inf_index = round(frac * src_pm25, 4)
                obs_status = src_mon['monitoring_status']
                inf_status = "MONITORED_SOURCE_INFLUENCE"
            else:
                unmonitored_count += 1
                inf_index = np.nan
                obs_status = "UNMONITORED_SOURCE"
                inf_status = "UNMONITORED_SOURCE_NO_INFLUENCE"
                
            records.append({
                'target_grid_id': target_gid,
                'target_latitude': target_lat,
                'target_longitude': target_lon,
                'source_grid_id': src_id,
                'source_latitude': s_lat,
                'source_longitude': s_lon,
                'distance_km': dist_km,
                'daily_transport_fraction': frac,
                'particles_count': p_count,
                'total_particles': tot_p,
                'source_pm25_ugm3': src_pm25,
                'source_weighted_transport_influence_index': inf_index,
                'source_observation_status': obs_status,
                'influence_status': inf_status,
                'query_date': date_str,
                'horizon_hours': h_val,
                'is_ambient_aqi_prediction': False
            })
            
        df_res = pd.DataFrame(records)
        
        # 7. Sort according to ranking_metric
        if ranking_metric == 'source_weighted_transport_influence_index':
            df_res['has_inf'] = ~df_res['source_weighted_transport_influence_index'].isna()
            df_res = df_res.sort_values(
                by=['has_inf', 'source_weighted_transport_influence_index', 'daily_transport_fraction'],
                ascending=[False, False, False]
            ).drop(columns=['has_inf'])
        else:
            # Default: rank by transport_fraction descending, then distance ascending
            df_res = df_res.sort_values(
                by=['daily_transport_fraction', 'distance_km'],
                ascending=[False, True]
            )
            
        df_res.reset_index(drop=True, inplace=True)
        df_res['rank'] = range(1, len(df_res) + 1)
        
        # Standard column order
        col_order = [
            'rank', 'target_grid_id', 'target_latitude', 'target_longitude',
            'source_grid_id', 'source_latitude', 'source_longitude',
            'distance_km', 'daily_transport_fraction', 'particles_count',
            'total_particles', 'source_pm25_ugm3',
            'source_weighted_transport_influence_index',
            'source_observation_status', 'influence_status',
            'query_date', 'horizon_hours', 'is_ambient_aqi_prediction'
        ]
        df_res = df_res[col_order]
        
        # Ground rankings for separate regional context tabs
        cpcb_rankings = self.obs_provider.get_cpcb_aqi_ranking(date_str)
        openaq_rankings = self.obs_provider.get_openaq_pm25_ranking(date_str)
        
        t_elapsed = round(time.time() - t_start, 3)
        
        result_dict = {
            'status': 'SUCCESS',
            'query_type': 'TARGET_INFLUENCE',
            'query_date': date_str,
            'horizon_hours': h_val,
            'target_info': target_info,
            'target_monitoring_info': target_mon_info,
            'ranking_metric': ranking_metric,
            'total_candidate_sources': 1380,
            'sources_with_positive_transport': len(df_res),
            'monitored_sources_count': monitored_count,
            'unmonitored_sources_count': unmonitored_count,
            'results_table': df_res,
            'date_matched_cpcb_ranking': cpcb_rankings,
            'date_matched_openaq_ranking': openaq_rankings,
            'execution_time_seconds': t_elapsed,
            'cache_hit': False,
            'matrix_source': mat_source,
            'scientific_disclaimer': (
                "Scientific Integrity Notice: "
                "1. Transport fractions represent physical 2D dispersion probability from candidate sources reaching this target.\n"
                "2. Source-weighted influence index represents dispersed source-tracer attribution (ug/m3-equiv) and is NOT target ambient AQI.\n"
                "3. Sources with unmonitored air quality report NaN influence index; concentration values are never fabricated.\n"
                "4. These are candidate source grids with modeled physical pathways, not verified emission inventories."
            )
        }
        
        if use_cache:
            self.cache[cache_key] = result_dict
            
        return result_dict
