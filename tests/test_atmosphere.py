import unittest
from src.physics.atmosphere import pressure_to_altitude_isa, altitude_to_pressure_isa

class TestAtmosphere(unittest.TestCase):
    def test_isa_conversion(self):
        h = pressure_to_altitude_isa(1013.25)
        self.assertAlmostEqual(h, 0.0, places=2)
        
        p = altitude_to_pressure_isa(0.0)
        self.assertAlmostEqual(p, 1013.25, places=2)
        
        # 850 hPa is approx 1457 m
        h_850 = pressure_to_altitude_isa(850.0)
        self.assertAlmostEqual(h_850, 1457.3, places=1)
        
        # roundtrip
        p_round = altitude_to_pressure_isa(h_850)
        self.assertAlmostEqual(p_round, 850.0, places=2)

if __name__ == '__main__':
    unittest.main()
