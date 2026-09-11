import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import os
from shapely.geometry import Point, LineString

def plot_trajectory(city, target_grid_id):
    grid = gpd.read_file('data/processed/grid/india_50km_grid.geojson')
    
    fig, ax = plt.subplots(figsize=(10, 10))
    grid.boundary.plot(ax=ax, linewidth=0.5, color='gray', alpha=0.5)
    
    target_poly = grid[grid['grid_id'] == target_grid_id]
    target_poly.plot(ax=ax, color='red', alpha=0.5, label='Target')
    
    # Plot 24, 48, 72h
    colors = {24: 'blue', 48: 'green', 72: 'purple'}
    
    for hours in [24, 48, 72]:
        traj_file = f'data/processed/trajectories/traj_{target_grid_id}_{hours}h.csv'
        if not os.path.exists(traj_file):
            continue
        df = pd.read_csv(traj_file)
        if len(df) > 1:
            line = LineString(zip(df['longitude'], df['latitude']))
            gpd.GeoSeries([line]).plot(ax=ax, color=colors[hours], linewidth=2, label=f'{hours}h')
            
            # Start point
            ax.scatter(df.iloc[0]['longitude'], df.iloc[0]['latitude'], color='black', s=20, zorder=5)
            # End point
            ax.scatter(df.iloc[-1]['longitude'], df.iloc[-1]['latitude'], color=colors[hours], s=50, marker='x', zorder=5)
            
    ax.set_title(f'Lagrangian Trajectories for {city}')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.legend()
    
    plt.savefig(f'docs/{city}_trajectory.png', dpi=150, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    CITIES = {
        'Delhi': 'IND_047_021',
        'Mumbai': 'IND_026_012',
        'Varanasi': 'IND_040_032'
    }
    for city, gid in CITIES.items():
        plot_trajectory(city, gid)
