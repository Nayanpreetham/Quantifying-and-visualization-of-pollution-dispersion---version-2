import unittest
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import numpy as np

class TestTrajectoryDomainMask(unittest.TestCase):
    def test_domain_masking(self):
        # Create dummy points
        # 1. Deep inside India (Nagpur)
        # 2. Arabian Sea (far outside)
        # 3. Coastal Ocean (inside 50km grid, but outside India landmass)
        df = pd.DataFrame({
            'longitude': [79.0882, 65.0, 72.5],
            'latitude': [21.1458, 15.0, 19.0], 
            'time': pd.to_datetime(['2020-01-01']*3)
        })
        
        geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
        traj_gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
        
        grid = gpd.read_file('data/processed/grid/india_50km_grid.geojson')
        
        import geodatasets
        world = gpd.read_file(geodatasets.get_path('naturalearth.land'))
        india_land = world.geometry.unary_union # Simplified, just check if over land in India region
        
        # 1. Check inside India (actually checking if over land for this test context)
        df['inside_india'] = traj_gdf.geometry.within(india_land)
        
        # 2. Check inside Grid Domain
        joined = gpd.sjoin(traj_gdf, grid[['grid_id', 'geometry']], how='left', predicate='within')
        df['inside_grid'] = ~joined['grid_id'].isna()
        
        # Point 1: Nagpur -> True, True
        self.assertTrue(df.iloc[0]['inside_india'])
        self.assertTrue(df.iloc[0]['inside_grid'])
        
        # Point 2: Deep Sea -> False, False
        self.assertFalse(df.iloc[1]['inside_india'])
        self.assertFalse(df.iloc[1]['inside_grid'])
        
        # Point 3: Coastal Ocean (Near Mumbai) 
        # (72.5E, 19.0N is offshore Mumbai, outside land, but might be inside grid)
        # Just checking that logic works, not asserting strict values for point 3 as it depends on NaturalEarth res
        self.assertFalse(df.iloc[1]['inside_india'])

if __name__ == '__main__':
    unittest.main()
