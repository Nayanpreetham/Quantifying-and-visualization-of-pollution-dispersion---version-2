import xarray as xr
import pandas as pd
import numpy as np
import math

class KinematicTrajectoryModel:
    def __init__(self, era5_file):
        self.ds = xr.open_dataset(era5_file)
        
    def _get_wind_vector(self, lat, lon, time):
        """
        Extracts the 2D near-surface wind vector (u10, v10) at a given location and time.
        NOTE: This is a 2D near-surface pilot. It does not synthesize 3D upper-air winds.
        """
        try:
            m = self.ds.sel(longitude=lon, latitude=lat, method='nearest')
            m_t = m.sel(valid_time=time, method='nearest')
        except Exception:
            return 0.0, 0.0
            
        wd = float(m_t['wind_direction'].values)
        ws_10 = float(m_t['wind_speed'].values)
        
        # Meteorological wind direction is 'from'
        # A backward trajectory moves INTO the wind (towards the source).
        # Therefore, the backward velocity vector is exactly the meteorological wind direction 'from' angle.
        
        # Math angle for the 'from' direction:
        math_angle = math.radians((90 - wd) % 360)
        
        u_back = ws_10 * math.cos(math_angle)
        v_back = ws_10 * math.sin(math_angle)
        
        return u_back, v_back

    def run_backward_trajectory(self, lat_start, lon_start, time_start, hours=72, dt_sec=3600):
        """
        Runs a backward trajectory using RK4 integration.
        """
        points = []
        
        current_lat = lat_start
        current_lon = lon_start
        current_time = pd.to_datetime(time_start)
        
        points.append({
            'time': current_time,
            'latitude': current_lat,
            'longitude': current_lon,
            'hour_backward': 0,
            'u_back': 0.0,
            'v_back': 0.0
        })
        
        num_steps = int(hours * 3600 / dt_sec)
        
        for step in range(1, num_steps + 1):
            # RK4 Integration Implementation
            def get_uv(lat, lon, dt_offset=0):
                t_eval = current_time - pd.Timedelta(seconds=dt_offset)
                return self._get_wind_vector(lat, lon, t_eval)
                
            def latlon_to_m(lat):
                lat_to_m = 111320.0
                lon_to_m = 111320.0 * math.cos(math.radians(lat))
                return lat_to_m, lon_to_m

            # k1
            u1, v1 = get_uv(current_lat, current_lon, 0)
            if u1 == 0 and v1 == 0:
                break
                
            lat_m, lon_m = latlon_to_m(current_lat)
            k1_lat = v1 / lat_m
            k1_lon = u1 / lon_m
            
            # k2
            lat2 = current_lat + 0.5 * dt_sec * k1_lat
            lon2 = current_lon + 0.5 * dt_sec * k1_lon
            u2, v2 = get_uv(lat2, lon2, dt_sec / 2.0)
            lat_m2, lon_m2 = latlon_to_m(lat2)
            k2_lat = v2 / lat_m2
            k2_lon = u2 / lon_m2
            
            # k3
            lat3 = current_lat + 0.5 * dt_sec * k2_lat
            lon3 = current_lon + 0.5 * dt_sec * k2_lon
            u3, v3 = get_uv(lat3, lon3, dt_sec / 2.0)
            lat_m3, lon_m3 = latlon_to_m(lat3)
            k3_lat = v3 / lat_m3
            k3_lon = u3 / lon_m3
            
            # k4
            lat4 = current_lat + dt_sec * k3_lat
            lon4 = current_lon + dt_sec * k3_lon
            u4, v4 = get_uv(lat4, lon4, dt_sec)
            lat_m4, lon_m4 = latlon_to_m(lat4)
            k4_lat = v4 / lat_m4
            k4_lon = u4 / lon_m4
            
            current_lat += (dt_sec / 6.0) * (k1_lat + 2*k2_lat + 2*k3_lat + k4_lat)
            current_lon += (dt_sec / 6.0) * (k1_lon + 2*k2_lon + 2*k3_lon + k4_lon)
            current_time -= pd.Timedelta(seconds=dt_sec)
            
            if (step * dt_sec) % 3600 == 0:
                points.append({
                    'time': current_time,
                    'latitude': current_lat,
                    'longitude': current_lon,
                    'hour_backward': int(step * dt_sec / 3600),
                    'u_back': u1,
                    'v_back': v1
                })
                
        return pd.DataFrame(points)
