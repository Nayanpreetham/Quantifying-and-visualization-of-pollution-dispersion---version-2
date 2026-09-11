import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import geodatasets
import os

_COUNTRIES_GDF = None
_GRID_GDF = None

def get_countries():
    global _COUNTRIES_GDF
    if _COUNTRIES_GDF is None:
        try:
            url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
            _COUNTRIES_GDF = gpd.read_file(url)
            # Simplify geometry drastically for point-in-polygon speed!
            _COUNTRIES_GDF['geometry'] = _COUNTRIES_GDF['geometry'].simplify(tolerance=0.1, preserve_topology=False)
        except:
            _COUNTRIES_GDF = pd.DataFrame()
    return _COUNTRIES_GDF

def get_grid(grid_geojson):
    global _GRID_GDF
    if _GRID_GDF is None:
        _GRID_GDF = gpd.read_file(grid_geojson)
    return _GRID_GDF

def calculate_ensemble_influence(ensemble_df, grid_geojson, target_id):
    """
    Computes ensemble-based transport influence T_i.
    ensemble_df contains multiple trajectories stacked together.
    """
    grid = get_grid(grid_geojson)
    
    geometry = [Point(xy) for xy in zip(ensemble_df['longitude'], ensemble_df['latitude'])]
    traj_gdf = gpd.GeoDataFrame(ensemble_df, geometry=geometry, crs='EPSG:4326')
    
    # Grid intersection
    joined = gpd.sjoin(traj_gdf, grid[['grid_id', 'geometry']], how='left', predicate='within')
    
    # Country classification using cached geojson
    countries = get_countries()
    if not countries.empty:
        joined_countries = gpd.sjoin(traj_gdf, countries[['name', 'geometry']], how='left', predicate='within')
        traj_gdf['country'] = joined_countries['name'].fillna('Ocean')
    else:
        traj_gdf['country'] = 'Unknown'
        
    total_points = len(joined)
    if total_points == 0:
        return pd.DataFrame()
        
    inside_grid = joined.dropna(subset=['grid_id'])
    
    if len(inside_grid) > 0:
        influence = inside_grid.groupby('grid_id').size().reset_index(name='ensemble_residence_points')
        influence['transport_weight'] = influence['ensemble_residence_points'] / total_points
    else:
        influence = pd.DataFrame(columns=['grid_id', 'ensemble_residence_points', 'transport_weight'])
        
    influence['target_grid_id'] = target_id
    
    # Calculate country fractions
    country_counts = traj_gdf['country'].value_counts(normalize=True) * 100.0
    for country, frac in country_counts.items():
        influence[f'frac_{country}'] = frac
        
    # Calculate outside domain fraction (not in any 50km grid)
    outside_grid = len(joined[joined['grid_id'].isna()])
    influence['frac_outside_domain'] = (outside_grid / total_points) * 100.0
    
    influence = influence.rename(columns={'grid_id': 'source_grid_id'})
    return influence
