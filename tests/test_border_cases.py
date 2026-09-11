import unittest
import pandas as pd
from src.transport.source_receptor import calculate_ensemble_influence

class TestBorderCases(unittest.TestCase):
    def test_mumbai_arabian_sea(self):
        # Mumbai offshore coordinates
        df = pd.DataFrame({
            'longitude': [72.0, 71.5, 71.0],
            'latitude': [19.0, 19.1, 19.2],
            'time': pd.to_datetime(['2020-01-01']*3)
        })
        
        inf = calculate_ensemble_influence(df, 'data/processed/grid/india_50km_grid.geojson', 'IND_026_012')
        
        # Should be ocean! 
        if 'frac_Ocean' in inf.columns:
            self.assertEqual(inf['frac_Ocean'].iloc[0], 100.0)
            
    def test_delhi_pakistan(self):
        # Pakistan coordinates
        df = pd.DataFrame({
            'longitude': [74.0, 73.5, 73.0],
            'latitude': [31.5, 31.6, 31.7], # Lahore area
            'time': pd.to_datetime(['2020-01-01']*3)
        })
        inf = calculate_ensemble_influence(df, 'data/processed/grid/india_50km_grid.geojson', 'IND_047_021')
        
        if 'frac_Pakistan' in inf.columns:
            self.assertEqual(inf['frac_Pakistan'].iloc[0], 100.0)

if __name__ == '__main__':
    unittest.main()
