import unittest
import math
import numpy as np

class Dummy3DModel:
    def __init__(self, u, v, w, sp_hpa=1000):
        self.u = u
        self.v = v
        self.w = w
        self.sp_hpa = sp_hpa
        
    def _get_interpolated_wind(self, lat, lon, level_hpa, time):
        if level_hpa > self.sp_hpa:
            # Masked by surface
            return 0.0, 0.0, 0.0
        return -self.u, -self.v, -self.w

    def run_backward_trajectory_3d(self, lat_start, lon_start, p_start_hpa, time_start, hours=1, dt_sec=3600):
        current_lat = lat_start
        current_lon = lon_start
        current_p = p_start_hpa
        
        num_steps = int(hours * 3600 / dt_sec)
        
        for step in range(1, num_steps + 1):
            def get_uvw(lat, lon, p, dt_offset=0):
                return self._get_interpolated_wind(lat, lon, p, time_start)
                
            def latlon_to_m(lat):
                lat_to_m = 111320.0
                lon_to_m = 111320.0 * math.cos(math.radians(lat))
                return lat_to_m, lon_to_m

            # k1
            u1, v1, w1 = get_uvw(current_lat, current_lon, current_p, 0)
            lat_m, lon_m = latlon_to_m(current_lat)
            k1_lat = v1 / lat_m
            k1_lon = u1 / lon_m
            k1_p = w1
            
            # Simplified RK4 for constant wind is just Euler
            current_lat += dt_sec * k1_lat
            current_lon += dt_sec * k1_lon
            current_p += dt_sec * k1_p
            
        return current_lat, current_lon, current_p

class TestTrajectory3DAnalytical(unittest.TestCase):
    
    def test_test6_horizontal_no_omega(self):
        # u=10, v=0, w=0 (Wind towards East, backward trajectory should move West)
        model = Dummy3DModel(10.0, 0.0, 0.0)
        lat, lon, p = model.run_backward_trajectory_3d(0, 0, 850, "2020", hours=1)
        # 10 m/s for 1 hour = 36000 m West
        # 1 deg lon at equator = 111320 m
        expected_lon = -36000.0 / 111320.0
        self.assertAlmostEqual(lon, expected_lon, places=3)
        self.assertEqual(lat, 0.0)
        self.assertEqual(p, 850)
        
    def test_test7_vertical_only(self):
        # u=0, v=0, w=0.1 hPa/s (Downwards)
        model = Dummy3DModel(0.0, 0.0, 0.1)
        lat, lon, p = model.run_backward_trajectory_3d(0, 0, 850, "2020", hours=1)
        # backward trajectory goes upwards (lower pressure)
        # dp = -0.1 * 3600 = -360 hPa
        self.assertEqual(lat, 0.0)
        self.assertEqual(lon, 0.0)
        self.assertAlmostEqual(p, 850 - 360, places=3)
        
    def test_test8_3d(self):
        model = Dummy3DModel(10.0, 10.0, 0.01)
        lat, lon, p = model.run_backward_trajectory_3d(0, 0, 850, "2020", hours=1)
        expected_lat = -36000.0 / 111320.0
        expected_lon = -36000.0 / 111320.0
        expected_p = 850 - (0.01 * 3600)
        self.assertAlmostEqual(lat, expected_lat, places=3)
        self.assertAlmostEqual(lon, expected_lon, places=3)
        self.assertAlmostEqual(p, expected_p, places=3)
        
    def test_test10_surface_masking(self):
        # w=0.1 hPa/s (downwards), backward goes upwards unless masked
        # If we start below ground (sp=900, we start at 950)
        model = Dummy3DModel(10.0, 0.0, 0.1, sp_hpa=900)
        lat, lon, p = model.run_backward_trajectory_3d(0, 0, 950, "2020", hours=1)
        # Should return 0,0,0 velocity because we are underground
        self.assertEqual(lat, 0.0)
        self.assertEqual(lon, 0.0)
        self.assertEqual(p, 950)

if __name__ == '__main__':
    unittest.main()
