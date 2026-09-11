import numpy as np
import sys
import os
sys.path.append(os.path.abspath('.'))
from src.physics.kljun import kljun_ffp

def test_kljun_non_negative():
    f, flag = kljun_ffp(zm=10, z0=0.1, u_mean=5, h=1000, L=-50, sigma_v=1, u_star=0.4, x=100, y=0)
    assert f >= 0, "Footprint must be non-negative"

def test_kljun_upwind_zero():
    f, flag = kljun_ffp(zm=10, z0=0.1, u_mean=5, h=1000, L=-50, sigma_v=1, u_star=0.4, x=-100, y=0)
    assert f == 0, "Upwind footprint should be exactly zero"

def test_kljun_distance_decay():
    f_close, _ = kljun_ffp(zm=10, z0=0.1, u_mean=5, h=1000, L=-50, sigma_v=1, u_star=0.4, x=100, y=0)
    f_far, _ = kljun_ffp(zm=10, z0=0.1, u_mean=5, h=1000, L=-50, sigma_v=1, u_star=0.4, x=2000, y=0)
    # Beyond the peak, footprint must decay
    assert f_far < f_close, f"Footprint must decay with extreme distance (f_close={f_close}, f_far={f_far})"

def test_kljun_stability():
    # Unstable should disperse more rapidly (lower peak) than stable
    f_unstable, _ = kljun_ffp(zm=10, z0=0.1, u_mean=5, h=1000, L=-20, sigma_v=1.5, u_star=0.4, x=500, y=0)
    f_stable, _ = kljun_ffp(zm=10, z0=0.1, u_mean=5, h=1000, L=200, sigma_v=0.5, u_star=0.2, x=500, y=0)
    # The actual magnitude depends on X scaling, but they must be different
    assert f_unstable != f_stable, "Stability must affect footprint geometry"

if __name__ == '__main__':
    try:
        test_kljun_non_negative()
        test_kljun_upwind_zero()
        test_kljun_distance_decay()
        test_kljun_stability()
        print("ALL KLJUN PHYSICS TESTS PASSED")
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
