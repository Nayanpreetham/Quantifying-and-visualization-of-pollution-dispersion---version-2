"""
Setup Geographic Boundaries and District-to-Grid Mappings
Downloads and processes:
1. Asia/Regional countries GeoJSON (Level 1)
2. Indian States & UTs GeoJSON (Level 2)
3. Indian Districts GeoJSON (Level 3)
4. Builds fast District/State centroid lookup mapping to 50 km model grid cells.
"""

import os
import json
import urllib.request
import numpy as np
import pandas as pd

def main():
    geo_dir = os.path.join("data", "processed", "geography")
    os.makedirs(geo_dir, exist_ok=True)
    
    # 1. Download World / Asia countries
    world_url = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson"
    print("Fetching World / Asia GeoJSON...")
    req = urllib.request.Request(world_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        world_data = json.loads(r.read().decode('utf-8'))
        
    asia_countries = {
        'India', 'Pakistan', 'China', 'Nepal', 'Bhutan', 'Bangladesh', 'Myanmar',
        'Sri Lanka', 'Afghanistan', 'Iran', 'Maldives', 'Thailand', 'Oman', 'United Arab Emirates'
    }
    asia_features = []
    for f in world_data.get('features', []):
        name = f.get('properties', {}).get('name', '')
        cont = f.get('properties', {}).get('continent', '')
        if name in asia_countries or cont == 'Asia':
            asia_features.append(f)
            
    asia_path = os.path.join(geo_dir, "asia_countries.geojson")
    with open(asia_path, 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': asia_features}, f)
    print(f"Saved {asia_path} with {len(asia_features)} features.")

    # 2. Download Indian States
    states_url = "https://raw.githubusercontent.com/Subhash9325/GeoJson-Data-of-Indian-States/master/Indian_States"
    print("Fetching Indian States GeoJSON...")
    req = urllib.request.Request(states_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        states_data = json.loads(r.read().decode('utf-8'))
        
    states_path = os.path.join(geo_dir, "india_states.geojson")
    with open(states_path, 'w', encoding='utf-8') as f:
        json.dump(states_data, f)
    print(f"Saved {states_path} with {len(states_data.get('features', []))} features.")

    # 3. Download Indian Districts
    districts_url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    print("Fetching Indian Districts GeoJSON...")
    req = urllib.request.Request(districts_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        districts_data = json.loads(r.read().decode('utf-8'))
        
    districts_path = os.path.join(geo_dir, "india_districts.geojson")
    with open(districts_path, 'w', encoding='utf-8') as f:
        json.dump(districts_data, f)
    print(f"Saved {districts_path} with {len(districts_data.get('features', []))} features.")

    # 4. Build District/State-to-50km-Grid Mapping
    print("Building District to 50 km Grid Cell Lookup Table...")
    grid_geojson_path = os.path.join("results", "phase18_grid_audit", "india_50km_grid.geojson")
    with open(grid_geojson_path, 'r', encoding='utf-8') as f:
        grid_data = json.load(f)
        
    grid_cells = []
    for feat in grid_data['features']:
        props = feat['properties']
        grid_cells.append({
            'grid_id_50km': props['grid_id_50km'],
            'lat': props['center_latitude_deg'],
            'lon': props['center_longitude_deg']
        })
    df_grid = pd.DataFrame(grid_cells)

    def find_nearest_grid(lat, lon):
        dists = (df_grid['lat'] - lat)**2 + (df_grid['lon'] - lon)**2
        nearest_idx = dists.idxmin()
        nearest_row = df_grid.iloc[nearest_idx]
        offset_km = np.sqrt(dists.min()) * 111.0
        return nearest_row['grid_id_50km'], nearest_row['lat'], nearest_row['lon'], float(offset_km)

    def compute_centroid(geometry):
        coords = []
        gtype = geometry.get('type')
        raw_coords = geometry.get('coordinates', [])
        
        def extract_coords(c_list):
            if not c_list:
                return
            if isinstance(c_list[0], (int, float)):
                coords.append((c_list[0], c_list[1]))
            elif isinstance(c_list[0], list):
                for item in c_list:
                    extract_coords(item)
                    
        extract_coords(raw_coords)
        if coords:
            arr = np.array(coords)
            # GeoJSON is [lon, lat]
            mean_lon = float(np.mean(arr[:, 0]))
            mean_lat = float(np.mean(arr[:, 1]))
            return mean_lat, mean_lon
        return None, None

    hierarchy = {}
    for feat in districts_data.get('features', []):
        props = feat.get('properties', {})
        state = props.get('NAME_1', '').strip()
        district = props.get('NAME_2', '').strip()
        if not state or not district:
            continue
            
        geom = feat.get('geometry', {})
        c_lat, c_lon = compute_centroid(geom)
        if c_lat is not None and c_lon is not None:
            gid, g_lat, g_lon, offset = find_nearest_grid(c_lat, c_lon)
            if state not in hierarchy:
                hierarchy[state] = {}
            hierarchy[state][district] = {
                'district_name': district,
                'state_name': state,
                'centroid_lat': round(c_lat, 4),
                'centroid_lon': round(c_lon, 4),
                'grid_id_50km': gid,
                'grid_lat': round(g_lat, 4),
                'grid_lon': round(g_lon, 4),
                'offset_km': round(offset, 1)
            }

    mapping_path = os.path.join(geo_dir, "district_to_grid_mapping.json")
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)
    print(f"Saved {mapping_path} with {len(hierarchy)} states and {sum(len(d) for d in hierarchy.values())} districts.")
    print("Geographic data setup complete!")

if __name__ == "__main__":
    main()
