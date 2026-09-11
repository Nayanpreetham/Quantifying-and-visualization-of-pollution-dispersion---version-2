import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
from pyproj import CRS

st.set_page_config(page_title="India Pollution Transport & Source Contribution", layout="wide")

st.title("India 50km Grid: Footprint-Weighted Pollution Contribution")
st.warning("**METHODOLOGICAL NOTE:** AQI is an index, not a conserved physical mass. The values shown represent a 'footprint-weighted estimated pollution contribution' and 'source-grid influence', which serve as an index-level approximation of upstream pollution impact, not an exact mass transport calculation.")

st.sidebar.header("Input Parameters")
target_lat = st.sidebar.number_input("Target Latitude", value=28.6139, format="%.4f")
target_lon = st.sidebar.number_input("Target Longitude", value=77.2090, format="%.4f")
target_date = st.sidebar.date_input("Target Date", pd.to_datetime('2020-01-01'))

@st.cache_data
def load_grid():
    grid_path = 'data/processed/grid/india_50km_grid.geojson'
    if os.path.exists(grid_path):
        return gpd.read_file(grid_path)
    return None

grid = load_grid()

if grid is not None:
    st.sidebar.success("Grid loaded successfully.")
    
    from shapely.geometry import Point
    target_pt = gpd.GeoDataFrame(geometry=[Point(target_lon, target_lat)], crs="EPSG:4326")
    distances = grid.geometry.distance(target_pt.geometry[0])
    closest_idx = distances.idxmin()
    target_grid = grid.iloc[closest_idx]
    
    st.header(f"Target Grid: {target_grid['grid_id']}")
    st.write(f"Centroid: {target_grid['center_lat']:.4f} N, {target_grid['center_lon']:.4f} E")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        m = folium.Map(location=[target_lat, target_lon], zoom_start=5)
        target_geojson = gpd.GeoSeries([target_grid.geometry]).to_json()
        folium.GeoJson(target_geojson, style_function=lambda x: {'color': 'red', 'fillColor': 'red'}).add_to(m)
        
        contrib_path = f"data/processed/contributions/contributions_{target_grid['grid_id']}.csv"
        if os.path.exists(contrib_path):
            contrib = pd.read_csv(contrib_path)
            st.success("Estimated pollution contributions loaded.")
            
            for _, row in contrib.iterrows():
                if row['rank'] <= 5: # Only map top 5
                    src_cell = grid[grid['grid_id'] == row['source_grid_id']]
                    if not src_cell.empty:
                        src_geom = gpd.GeoSeries(src_cell.geometry).to_json()
                        folium.GeoJson(src_geom, style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.4}).add_to(m)
                    
            st_folium(m, width=700, height=500)
            
            with col2:
                st.subheader("ERA5 Meteorological Conditions")
                st.write(f"**Wind Speed**: {contrib.iloc[0]['wind_speed']:.2f} m/s")
                st.write(f"**Wind Direction**: {contrib.iloc[0]['wind_direction']:.2f}°")
                st.write("**Model Quality**: VALID (Uncertainty not yet quantified for V1)")
            
            st.subheader("Contributing Source Grids")
            
            top5_share = contrib[contrib['rank'] <= 5]['contribution_percent'].sum()
            remaining_share = contrib[contrib['rank'] == 999]['contribution_percent'].sum() if 999 in contrib['rank'].values else 100 - top5_share
            
            st.write(f"**Top 5 Share**: {top5_share:.1f}% | **Remaining Sources**: {remaining_share:.1f}%")
            
            display_cols = ['rank', 'source_grid_id', 'distance_km', 'baseline_pollution_indicator', 'footprint_weight', 'estimated_pollution_contribution', 'contribution_percent']
            # Safely select available columns
            display_cols = [c for c in display_cols if c in contrib.columns]
            st.dataframe(contrib[display_cols])
            
        else:
            st.warning(f"No contribution data found for {target_grid['grid_id']}.")
            st_folium(m, width=700, height=500)
else:
    st.error("Grid file not found.")
