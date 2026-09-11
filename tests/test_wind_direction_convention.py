import unittest
import math
import numpy as np

class TestWindDirectionConvention(unittest.TestCase):
    
    def calculate_backward_velocity(self, wd_deg, ws_m_s):
        """
        Given wind direction (FROM where wind originates, 0=N, 90=E)
        Return backward trajectory velocity (u_back, v_back).
        A backward trajectory moves INTO the wind, so its velocity vector
        is pointing towards the direction the wind came FROM.
        """
        math_angle = math.radians((90 - wd_deg) % 360)
        u_back = ws_m_s * math.cos(math_angle)
        v_back = ws_m_s * math.sin(math_angle)
        return u_back, v_back

    def test_eastward_wind(self):
        """
        Test 1: Constant uniform eastward wind (wind blowing TOWARDS East).
        This means wind is FROM West (270 deg).
        Backward trajectory must move westward (u < 0, v = 0).
        """
        u_back, v_back = self.calculate_backward_velocity(270, 10.0)
        self.assertAlmostEqual(u_back, -10.0, places=5)
        self.assertAlmostEqual(v_back, 0.0, places=5)
        
    def test_northward_wind(self):
        """
        Test 2: Constant uniform northward wind (wind blowing TOWARDS North).
        This means wind is FROM South (180 deg).
        Backward trajectory must move southward (u = 0, v < 0).
        """
        u_back, v_back = self.calculate_backward_velocity(180, 10.0)
        self.assertAlmostEqual(u_back, 0.0, places=5)
        self.assertAlmostEqual(v_back, -10.0, places=5)
        
    def test_zero_wind(self):
        """
        Test 3: Zero wind. Trajectory must remain stationary.
        """
        u_back, v_back = self.calculate_backward_velocity(45, 0.0)
        self.assertAlmostEqual(u_back, 0.0, places=5)
        self.assertAlmostEqual(v_back, 0.0, places=5)
        
    def test_analytical_displacement(self):
        """
        Test 4: Constant wind with known analytical displacement.
        Wind from NW (315 deg) at 10 m/s.
        Air moves SE. Backward trajectory moves NW.
        NW vector: u < 0, v > 0.
        u = -10 * cos(45) = -7.071, v = 10 * sin(45) = 7.071.
        Displacement after 1 hour (3600s):
        dx = -7.071 * 3600 = -25455.8 m
        dy = 7.071 * 3600 = 25455.8 m
        """
        u_back, v_back = self.calculate_backward_velocity(315, 10.0)
        self.assertAlmostEqual(u_back, -7.0710678, places=5)
        self.assertAlmostEqual(v_back, 7.0710678, places=5)
        
        dx = u_back * 3600
        dy = v_back * 3600
        
        self.assertAlmostEqual(dx, -25455.844, places=2)
        self.assertAlmostEqual(dy, 25455.844, places=2)

if __name__ == '__main__':
    unittest.main()
