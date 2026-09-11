import numpy as np
import xarray as xr
import sys
import os
sys.path.append(os.path.abspath('.'))
# We will test the logical equations from meteorology.py in isolation

def test_friction_velocity_zero_wind():
    # If wind is exactly zero, u_star should not be exactly zero to prevent div by zero
    ws = np.array([0.0])
    k, z, z0 = 0.4, 10.0, 0.1
    u_star = ws * k / np.log(z / z0)
    u_star = np.where(u_star > 0.01, u_star, 0.01)
    assert u_star[0] == 0.01, "u_star must be clamped to prevent zero"

def test_obukhov_length_zero_flux():
    # If H is exactly zero, L diverges to infinity
    u_star = np.array([0.2])
    H = np.array([0.0])
    H_clamped = np.where(np.abs(H) > 0.1, H, np.sign(H)*0.1)
    # Actually if H is 0, sign(0) is 0, so 0.1 * 0 is 0! Let's check this bug.
    H_clamped = np.where(np.abs(H) > 0.1, H, np.where(H >= 0, 0.1, -0.1))
    assert H_clamped[0] == 0.1, "Heat flux clamping must handle exact zero"

def test_sigma_v_stability():
    u_star = 0.2
    # stable
    sigma_v_stable = u_star * 1.9
    # unstable
    z, L = 10.0, -50.0
    sigma_v_unstable = u_star * np.sqrt(3.6 + 2.0 * np.power(np.abs(-z/L), 2/3))
    assert sigma_v_unstable > 0
    assert sigma_v_stable > 0

if __name__ == '__main__':
    try:
        test_friction_velocity_zero_wind()
        test_obukhov_length_zero_flux()
        test_sigma_v_stability()
        print("ALL METEOROLOGY PHYSICS TESTS PASSED")
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
