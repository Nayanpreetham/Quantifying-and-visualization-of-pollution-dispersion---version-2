"""
Observation Provider for Phase 20 Interactive Application
Phase 20 - Interactive National Pollution Dispersion Query Application

Provides fast, date-matched lookups and regional rankings for:
1. CPCB Official Daily AQI Bulletins (City-level regulatory AQI index [0-500]).
2. OpenAQ Station-Level PM2.5 Hourly Measurements (Physical concentration [ug/m3]).
3. Grid Cell Monitoring Status and Baseline Concentration Mapping.

Rules:
- Strictly distinguishes measured pollutant concentrations (ug/m3) from regulatory AQI index values.
- Never computes synthetic AQI from arbitrary formulas.
- Clearly flags ground observations as independent measurements, distinct from modeled transport fractions.
"""

import os
import glob
import pandas as pd
import numpy as np

CPCB_PARQUET_PATH = "data/processed/cpcb_bulletins_unified.parquet"
OPENAQ_PARQUET_PATH = "data/processed/openaq_pm25_observations.parquet"
STATION_MAP_CSV = "results/phase18_grid_audit/station_to_50km_grid_mapping.csv"
MONITORED_SUMMARY_CSV = "results/phase19_transport/matrices/monitored_cells_concentration_summary.csv"


class ObservationProvider:
    def __init__(self,
                 cpcb_parquet=CPCB_PARQUET_PATH,
                 openaq_parquet=OPENAQ_PARQUET_PATH,
                 station_map_csv=STATION_MAP_CSV,
                 monitored_summary_csv=MONITORED_SUMMARY_CSV):
        self.cpcb_parquet = cpcb_parquet
        self.openaq_parquet = openaq_parquet
        self.station_map_csv = station_map_csv
        self.monitored_summary_csv = monitored_summary_csv
        
        self._df_station_map = None
        self._df_monitored_summary = None
        self._monitored_pm25_lookup = {}
        self._cell_to_stations = {}
        
        self._init_mappings()

    def _init_mappings(self):
        """Loads static station-to-grid mapping and multi-year monitored summaries."""
        if os.path.exists(self.station_map_csv):
            self._df_station_map = pd.read_csv(self.station_map_csv)
            for _, r in self._df_station_map.iterrows():
                gid = r['grid_id_50km']
                if gid not in self._cell_to_stations:
                    self._cell_to_stations[gid] = []
                self._cell_to_stations[gid].append({
                    'station_id': r['station_id'],
                    'station_name': r['station_name'],
                    'city': r.get('corrected_city', r.get('original_city', ''))
                })
                
        if os.path.exists(self.monitored_summary_csv):
            self._df_monitored_summary = pd.read_csv(self.monitored_summary_csv)
            self._monitored_pm25_lookup = dict(zip(
                self._df_monitored_summary['grid_id_50km'],
                self._df_monitored_summary['mean_observed_pm25_ugm3']
            ))
            
        self._city_to_grid_info = {}
        if self._df_station_map is not None:
            for city_raw, group in self._df_station_map.groupby(self._df_station_map['corrected_city'].str.strip().str.lower()):
                unique_cells = sorted(group['grid_id_50km'].unique().tolist())
                city_proper = group['corrected_city'].iloc[0]
                if len(unique_cells) == 1:
                    self._city_to_grid_info[city_raw] = {
                        'grid_id_50km': unique_cells[0],
                        'spatial_mapping_type': 'SINGLE_50KM_CELL',
                        'city_name': city_proper
                    }
                else:
                    self._city_to_grid_info[city_raw] = {
                        'grid_id_50km': f"MULTIPLE_CELLS ({', '.join(unique_cells)})",
                        'spatial_mapping_type': 'MULTI_50KM_CELL_URBAN_AREA',
                        'city_name': city_proper
                    }

    def get_cpcb_aqi_ranking(self, date_str):
        """
        Retrieves date-matched CPCB Daily AQI Bulletin values across Indian cities.
        
        Assigns 50 km grid ID where a defensible station-level mapping exists:
        - Single-cell city: Assigned exact 50 km grid ID ('SINGLE_50KM_CELL').
        - Multi-cell city: Labeled 'MULTIPLE_CELLS (...)' ('MULTI_50KM_CELL_URBAN_AREA').
        - Unmapped bulletin: Labeled 'UNMAPPED' ('CITY_LEVEL_REGULATORY_BULLETIN').
        
        Returns:
            pd.DataFrame: Columns ['rank', 'city', 'grid_id_50km', 'spatial_mapping_type',
                                   'aqi_index_value', 'air_quality_category',
                                   'prominent_pollutant', 'no_stations_reporting', 'observation_date', 'data_source']
        """
        if not os.path.exists(self.cpcb_parquet):
            return pd.DataFrame()
            
        try:
            df = pd.read_parquet(self.cpcb_parquet, filters=[('date', '==', date_str)])
            if df.empty:
                return pd.DataFrame()
                
            df['aqi'] = pd.to_numeric(df['aqi'], errors='coerce')
            # Handle missing AQI and deduplicate identical city reports on same date
            df_valid = df.dropna(subset=['aqi'])
            df_valid = df_valid.drop_duplicates(subset=['city'], keep='first')
            df_sorted = df_valid.sort_values(by='aqi', ascending=False).reset_index(drop=True)
            
            # Map grid IDs defensibly
            grid_ids = []
            mapping_types = []
            for c in df_sorted['city']:
                c_clean = str(c).strip().lower()
                if c_clean in self._city_to_grid_info:
                    info = self._city_to_grid_info[c_clean]
                    grid_ids.append(info['grid_id_50km'])
                    mapping_types.append(info['spatial_mapping_type'])
                else:
                    grid_ids.append('UNMAPPED')
                    mapping_types.append('CITY_LEVEL_REGULATORY_BULLETIN')
            
            # Format output table
            df_out = pd.DataFrame({
                'rank': df_sorted.index + 1,
                'city': df_sorted['city'],
                'grid_id_50km': grid_ids,
                'spatial_mapping_type': mapping_types,
                'aqi_index_value': df_sorted['aqi'].astype(int),
                'air_quality_category': df_sorted['air_quality'].fillna('Unspecified'),
                'prominent_pollutant': df_sorted['prominent_pollutant'].fillna('Unspecified'),
                'no_stations_reporting': df_sorted['no_stations'].fillna(1).astype(int),
                'observation_date': date_str,
                'data_source': 'CPCB Daily Air Quality Bulletin'
            })
            return df_out
        except Exception as e:
            print(f"Error querying CPCB parquet: {e}")
            return pd.DataFrame()

    def get_openaq_pm25_ranking(self, date_str):
        """
        Retrieves date-matched OpenAQ station-level PM2.5 observations.
        
        Returns:
            pd.DataFrame: Columns ['rank', 'city', 'station_name', 'grid_id_50km',
                                   'mean_observed_pm25_ugm3', 'observation_samples', 'observation_date', 'data_source']
        """
        if not os.path.exists(self.openaq_parquet):
            return pd.DataFrame()
            
        try:
            df = pd.read_parquet(self.openaq_parquet, filters=[('date', '==', date_str)])
            if df.empty:
                return pd.DataFrame()
                
            df['pm25'] = pd.to_numeric(df['pm25'], errors='coerce')
            df_valid = df.dropna(subset=['pm25'])
            if df_valid.empty:
                return pd.DataFrame()
                
            # Aggregate by station
            st_agg = df_valid.groupby(['city', 'station_id', 'station_name']).agg(
                mean_pm25=('pm25', 'mean'),
                count_samples=('pm25', 'count')
            ).reset_index()
            
            # Map grid ID
            if self._df_station_map is not None:
                st_id_to_grid = dict(zip(self._df_station_map['station_id'], self._df_station_map['grid_id_50km']))
                st_agg['grid_id_50km'] = st_agg['station_id'].map(st_id_to_grid).fillna('UNMAPPED')
            else:
                st_agg['grid_id_50km'] = 'UNMAPPED'
                
            st_sorted = st_agg.sort_values(by='mean_pm25', ascending=False).reset_index(drop=True)
            
            df_out = pd.DataFrame({
                'rank': st_sorted.index + 1,
                'city': st_sorted['city'],
                'station_name': st_sorted['station_name'],
                'grid_id_50km': st_sorted['grid_id_50km'],
                'mean_observed_pm25_ugm3': st_sorted['mean_pm25'].round(2),
                'observation_samples': st_sorted['count_samples'],
                'observation_date': date_str,
                'data_source': 'OpenAQ Ground CAAQMS (Measured PM2.5)'
            })
            return df_out
        except Exception as e:
            print(f"Error querying OpenAQ parquet: {e}")
            return pd.DataFrame()

    def get_source_cell_monitoring_info(self, grid_id, date_str):
        """
        Determines ground observation availability for a specific source 50 km cell on the query date.
        
        Returns:
            dict: Monitoring metadata and available PM2.5 values.
        """
        is_known_monitored_cell = grid_id in self._monitored_pm25_lookup
        historical_baseline_pm25 = self._monitored_pm25_lookup.get(grid_id, np.nan)
        stations = self._cell_to_stations.get(grid_id, [])
        station_names = [s['station_name'] for s in stations]
        station_cities = list(set(s['city'] for s in stations if s['city']))
        
        date_matched_pm25 = np.nan
        has_date_matched_obs = False
        sample_count = 0
        
        # Check if date-matched OpenAQ data exists for stations in this cell
        if stations and os.path.exists(self.openaq_parquet):
            station_ids = [s['station_id'] for s in stations]
            try:
                df_date = pd.read_parquet(self.openaq_parquet, filters=[('date', '==', date_str)])
                df_cell = df_date[df_date['station_id'].isin(station_ids)]
                if not df_cell.empty:
                    df_cell_valid = df_cell.dropna(subset=['pm25'])
                    if not df_cell_valid.empty:
                        date_matched_pm25 = round(float(df_cell_valid['pm25'].mean()), 2)
                        has_date_matched_obs = True
                        sample_count = len(df_cell_valid)
            except Exception:
                pass
                
        # Determine status
        if has_date_matched_obs:
            status = "DATE_MATCHED_GROUND_OBSERVATION"
            effective_pm25 = date_matched_pm25
            desc = f"Active ground monitoring: {sample_count} samples on {date_str} (mean {date_matched_pm25:.1f} ug/m3)"
        elif is_known_monitored_cell:
            status = "HISTORICAL_BASELINE_ONLY"
            effective_pm25 = historical_baseline_pm25
            desc = f"Monitored cell without data on {date_str}. Multi-year baseline: {historical_baseline_pm25:.1f} ug/m3"
        else:
            status = "UNMONITORED_SOURCE"
            effective_pm25 = np.nan
            desc = "Unmonitored terrestrial cell. No ground air-quality monitors installed."
            
        return {
            'grid_id_50km': grid_id,
            'monitoring_status': status,
            'has_date_matched_obs': has_date_matched_obs,
            'date_matched_pm25_ugm3': date_matched_pm25,
            'has_historical_baseline': is_known_monitored_cell,
            'historical_baseline_pm25_ugm3': historical_baseline_pm25,
            'effective_source_pm25_ugm3': effective_pm25,
            'stations_count': len(stations),
            'station_names': station_names,
            'cities': station_cities,
            'description': desc
        }
