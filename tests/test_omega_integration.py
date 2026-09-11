import unittest
import pandas as pd
import math
import numpy as np

# A simplified mock of the run_backward_trajectory_3d loop to test the pure RK4 math
def run_rk4_vertical(omega_hpa_s, start_p, dt_sec, num_steps):
    current_p = start_p
    points = [current_p]
    
    for _ in range(num_steps):
        # Forward omega is omega_hpa_s. Backward is -omega_hpa_s.
        # But wait, in the actual model:
        # get_uvw returns -u, -v, -omega
        w = -omega_hpa_s
        
        # k1
        k1_p = w
        # k2
        k2_p = w
        # k3
        k3_p = w
        # k4
        k4_p = w
        
        current_p += (dt_sec / 6.0) * (k1_p + 2*k2_p + 2*k3_p + k4_p)
        points.append(current_p)
        
    return points

class TestOmegaIntegration(unittest.TestCase):
    def test_omega_integration(self):
        # 0.01 hPa/s downward.
        # Backward trajectory should go UP in altitude, which means DOWN in pressure.
        omega = 0.01
        dt = 1800 # 30 min
        steps = 48 # 24 hours
        
        points = run_rk4_vertical(omega, 1000.0, dt, steps)
        
        final_p = points[-1]
        
        # Analytical integration:
        # p(t) = p0 - omega * t (since going backward)
        total_time = dt * steps
        analytical_p = 1000.0 - (omega * total_time)
        
        self.assertAlmostEqual(final_p, analytical_p, places=4)
        
        # Verify delta p / delta t matches integrated omega
        dp = points[-1] - points[0]
        actual_omega = dp / total_time
        
        # actual_omega should be exactly -omega (since we go backward)
        self.assertAlmostEqual(actual_omega, -omega, places=4)
        print(f"Integrated Vertical Motion matched: expected {-omega} hPa/s, got {actual_omega} hPa/s")

if __name__ == '__main__':
    unittest.main()
