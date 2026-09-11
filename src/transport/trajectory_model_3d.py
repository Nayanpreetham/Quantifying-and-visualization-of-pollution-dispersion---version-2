import xarray as xr
import pandas as pd
import numpy as np
import math
from scipy.interpolate import RegularGridInterpolator

class KinematicTrajectoryModel3D:
    def __init__(self, era5_3d_file, era5_surface_file):
        self.ds_3d = xr.open_dataset(era5_3d_file)
        self.ds_sfc = xr.open_dataset(era5_surface_file)
        
        self.ds_3d = self.ds_3d.sortby('pressure_level') 
        self.ds_3d = self.ds_3d.sortby('valid_time')
        self.ds_3d = self.ds_3d.sortby('latitude')
        self.ds_3d = self.ds_3d.sortby('longitude')
        
        # Load into memory for fast scipy interpolation
        self.times = self.ds_3d['valid_time'].values.astype('datetime64[s]').astype(float)
        self.levels = self.ds_3d['pressure_level'].values
        self.lats = self.ds_3d['latitude'].values
        self.lons = self.ds_3d['longitude'].values
        
        u_data = self.ds_3d['u'].values
        v_data = self.ds_3d['v'].values
        w_data = self.ds_3d['w'].values
        
        # RegularGridInterpolator expects points in the order of the dimensions
        # The dimensions are (valid_time, pressure_level, latitude, longitude)
        self.interp_u = RegularGridInterpolator((self.times, self.levels, self.lats, self.lons), u_data, bounds_error=False, fill_value=0.0)
        self.interp_v = RegularGridInterpolator((self.times, self.levels, self.lats, self.lons), v_data, bounds_error=False, fill_value=0.0)
        self.interp_w = RegularGridInterpolator((self.times, self.levels, self.lats, self.lons), w_data, bounds_error=False, fill_value=0.0)
        
        # Surface pressure interpolator
        self.ds_sfc = self.ds_sfc.sortby('valid_time')
        self.ds_sfc = self.ds_sfc.sortby('latitude')
        self.ds_sfc = self.ds_sfc.sortby('longitude')
        
        self.times_sfc = self.ds_sfc['valid_time'].values.astype('datetime64[s]').astype(float)
        self.lats_sfc = self.ds_sfc['latitude'].values
        self.lons_sfc = self.ds_sfc['longitude'].values
        sp_data = self.ds_sfc['sp'].values
        
        self.interp_sp = RegularGridInterpolator((self.times_sfc, self.lats_sfc, self.lons_sfc), sp_data, bounds_error=False, fill_value=101325.0)

    def _get_interpolated_wind(self, lat, lon, level_hpa, time_sec):
        # time_sec is already a float timestamp
        
        # Check surface pressure
        sp = self.interp_sp((time_sec, lat, lon))
        sp_hpa = float(sp) / 100.0
        
        if level_hpa > sp_hpa:
            level_hpa = sp_hpa
            
        u = float(self.interp_u((time_sec, level_hpa, lat, lon)))
        v = float(self.interp_v((time_sec, level_hpa, lat, lon)))
        w = float(self.interp_w((time_sec, level_hpa, lat, lon)))
        
        omega_hpa_s = w / 100.0
        
        return -u, -v, -omega_hpa_s

    def run_backward_trajectory_3d(self, lat_start, lon_start, p_start_hpa, time_start, hours=72, dt_sec=1800):
        points = []
        
        current_lat = lat_start
        current_lon = lon_start
        current_p = p_start_hpa
        current_time = pd.to_datetime(time_start)
        
        points.append({
            'time': current_time,
            'latitude': current_lat,
            'longitude': current_lon,
            'pressure_hpa': current_p,
            'hour_backward': 0
        })
        
        num_steps = int(hours * 3600 / dt_sec)
        
        for step in range(1, num_steps + 1):
            def get_uvw(lat, lon, p, dt_offset=0):
                t_eval = (current_time - pd.Timedelta(seconds=dt_offset)).timestamp()
                return self._get_interpolated_wind(lat, lon, p, t_eval)
                
            def latlon_to_m(lat):
                lat_to_m = 111320.0
                lon_to_m = 111320.0 * math.cos(math.radians(lat))
                return lat_to_m, lon_to_m

            # k1
            u1, v1, w1 = get_uvw(current_lat, current_lon, current_p, 0)
            if u1 == 0 and v1 == 0 and w1 == 0:
                break
                
            lat_m, lon_m = latlon_to_m(current_lat)
            k1_lat = v1 / lat_m
            k1_lon = u1 / lon_m
            k1_p = w1
            
            # k2
            lat2 = current_lat + 0.5 * dt_sec * k1_lat
            lon2 = current_lon + 0.5 * dt_sec * k1_lon
            p2 = current_p + 0.5 * dt_sec * k1_p
            u2, v2, w2 = get_uvw(lat2, lon2, p2, dt_sec / 2.0)
            lat_m2, lon_m2 = latlon_to_m(lat2)
            k2_lat = v2 / lat_m2
            k2_lon = u2 / lon_m2
            k2_p = w2
            
            # k3
            lat3 = current_lat + 0.5 * dt_sec * k2_lat
            lon3 = current_lon + 0.5 * dt_sec * k2_lon
            p3 = current_p + 0.5 * dt_sec * k2_p
            u3, v3, w3 = get_uvw(lat3, lon3, p3, dt_sec / 2.0)
            lat_m3, lon_m3 = latlon_to_m(lat3)
            k3_lat = v3 / lat_m3
            k3_lon = u3 / lon_m3
            k3_p = w3
            
            # k4
            lat4 = current_lat + dt_sec * k3_lat
            lon4 = current_lon + dt_sec * k3_lon
            p4 = current_p + dt_sec * k3_p
            u4, v4, w4 = get_uvw(lat4, lon4, p4, dt_sec)
            lat_m4, lon_m4 = latlon_to_m(lat4)
            k4_lat = v4 / lat_m4
            k4_lon = u4 / lon_m4
            k4_p = w4
            
            current_lat += (dt_sec / 6.0) * (k1_lat + 2*k2_lat + 2*k3_lat + k4_lat)
            current_lon += (dt_sec / 6.0) * (k1_lon + 2*k2_lon + 2*k3_lon + k4_lon)
            current_p += (dt_sec / 6.0) * (k1_p + 2*k2_p + 2*k3_p + k4_p)
            current_time -= pd.Timedelta(seconds=dt_sec)
            
            if current_p < 500:
                current_p = 500
                
            if (step * dt_sec) % 3600 == 0:
                points.append({
                    'time': current_time,
                    'latitude': current_lat,
                    'longitude': current_lon,
                    'pressure_hpa': current_p,
                    'hour_backward': int(step * dt_sec / 3600)
                })
                
        return pd.DataFrame(points)
