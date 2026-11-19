"""
Setup Geographic Boundaries and District-to-Grid Mappings
Downloads and processes official Indian Sovereign Geographical Datasets:
1. asia_countries.geojson: Asian continent context reflecting India's complete sovereign boundaries.
2. india_national_web.geojson: Continuous national sovereign outline of the Republic of India.
3. india_states_web.geojson: Complete 36 States & Union Territories (including full J&K and Ladakh with PoK & CoK).
4. district_to_grid_mapping.json & grid_to_districts_mapping.json: Full district-to-50km-grid lookup tables.
"""

import os
import json
import urllib.request
from shapely.geometry import shape, mapping
from shapely.validation import make_valid

def main():
    geo_dir = os.path.join("data", "processed", "geography")
    os.makedirs(geo_dir, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. Asian Regional Context (with India's official perspective)
    print("1. Fetching world/Asian countries from official Indian perspective...")
    world_url = "https://raw.githubusercontent.com/RajShukla1/india-geojson/main/world-countries-india-view.geojson"
    req = urllib.request.Request(world_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        world_data = json.loads(r.read().decode("utf-8"))

    target_names = {
        'India', 'Pakistan', 'China', 'Nepal', 'Bhutan', 'Bangladesh', 'Myanmar',
        'Sri Lanka', 'Afghanistan', 'Iran', 'Maldives', 'Thailand', 'Oman',
        'United Arab Emirates', 'Saudi Arabia', 'Qatar', 'Kuwait', 'Iraq',
        'Kazakhstan', 'Uzbekistan', 'Turkmenistan', 'Tajikistan', 'Kyrgyzstan'
    }

    asia_features = []
    for f in world_data.get("features", []):
        props = f.get("properties", {})
        if not f.get("geometry"):
            continue
        raw_name = props.get("NAME", "")
        clean_name = "China" if "China" in raw_name else raw_name
        cont = props.get("CONTINENT", "")
        
        if cont == "Asia" or clean_name in target_names or raw_name in target_names:
            out_props = {
                "name": clean_name,
                "NAME": clean_name,
                "ISO3": props.get("ISO3", ""),
                "continent": cont
            }
            geom = make_valid(shape(f["geometry"])).simplify(0.005, preserve_topology=True)
            asia_features.append({
                "type": "Feature",
                "properties": out_props,
                "geometry": mapping(geom)
            })

    asia_path = os.path.join(geo_dir, "asia_countries.geojson")
    with open(asia_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": asia_features}, f)
    print(f"Saved {asia_path} with {len(asia_features)} features.")

    # 2. Indian National Sovereign Boundary Outline
    print("2. Fetching continuous Indian sovereign national outline...")
    outline_url = "https://raw.githubusercontent.com/RajShukla1/india-geojson/main/india-outline.geojson"
    req_out = urllib.request.Request(outline_url, headers=headers)
    with urllib.request.urlopen(req_out, timeout=30) as r:
        outline_data = json.loads(r.read().decode("utf-8"))

    out_feat = outline_data["features"][0]
    out_geom = make_valid(shape(out_feat["geometry"])).simplify(0.003, preserve_topology=True)
    national_collection = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "name": "India",
                "NAME_0": "India",
                "territory": "Sovereign Territory of India"
            },
            "geometry": mapping(out_geom)
        }]
    }
    national_path = os.path.join(geo_dir, "india_national_web.geojson")
    with open(national_path, "w", encoding="utf-8") as f:
        json.dump(national_collection, f)
    print(f"Saved {national_path}.")

    # 3. Indian States and Union Territories (36 States & UTs)
    print("3. Fetching Indian States and UTs (including full J&K and Ladakh)...")
    states_url = "https://raw.githubusercontent.com/RajShukla1/india-geojson/main/india-states.geojson"
    req_st = urllib.request.Request(states_url, headers=headers)
    with urllib.request.urlopen(req_st, timeout=30) as r:
        states_data = json.loads(r.read().decode("utf-8"))

    state_features = []
    for f in states_data.get("features", []):
        props = f.get("properties", {})
        s_name = props.get("name", "")
        geom = make_valid(shape(f["geometry"])).simplify(0.0035, preserve_topology=True)
        out_props = {
            "NAME_1": s_name,
            "name": s_name,
            "st_nm": s_name,
            "NAME_0": "India",
            "type": props.get("type", "state"),
            "region": props.get("region", "")
        }
        state_features.append({
            "type": "Feature",
            "properties": out_props,
            "geometry": mapping(geom)
        })

    states_path = os.path.join(geo_dir, "india_states_web.geojson")
    with open(states_path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": state_features}, f)
    print(f"Saved {states_path} with {len(state_features)} states/UTs.")

    # 4. Update District-to-Grid Hierarchy with Ladakh UT
    print("4. Updating District-to-Grid Hierarchy with Ladakh UT...")
    mapping_path = os.path.join(geo_dir, "district_to_grid_mapping.json")
    if os.path.exists(mapping_path):
        with open(mapping_path, "r", encoding="utf-8") as f:
            hierarchy = json.load(f)
            
        if "Ladakh" not in hierarchy:
            hierarchy["Ladakh"] = {}
            
        jk_data = hierarchy.get("Jammu and Kashmir", {})
        leh_info = jk_data.get("Ladakh (Leh)", {
            "district_name": "Leh (Ladakh)",
            "state_name": "Ladakh",
            "centroid_lat": 34.1526,
            "centroid_lon": 77.5771,
            "grid_id_50km": "IND_50KM_r056_c020",
            "grid_lat": 33.3782,
            "grid_lon": 78.1081,
            "offset_km": 31.9
        })
        kargil_info = jk_data.get("Kargil", {
            "district_name": "Kargil",
            "state_name": "Ladakh",
            "centroid_lat": 34.5539,
            "centroid_lon": 76.1349,
            "grid_id_50km": "IND_50KM_r056_c017",
            "grid_lat": 33.3521,
            "grid_lon": 76.4871,
            "offset_km": 29.0
        })
        
        hierarchy["Ladakh"]["Leh (Ladakh)"] = {**leh_info, "state_name": "Ladakh"}
        hierarchy["Ladakh"]["Kargil"] = {**kargil_info, "state_name": "Ladakh"}
        
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(hierarchy, f, indent=2)

    # 5. Update Reverse Grid-to-Districts Mapping
    rev_mapping_path = os.path.join(geo_dir, "grid_to_districts_mapping.json")
    if os.path.exists(rev_mapping_path):
        with open(rev_mapping_path, "r", encoding="utf-8") as f:
            rev_map = json.load(f)
            
        rev_map["IND_50KM_r056_c020"] = ["Leh (Ladakh)", "Ladakh"]
        rev_map["IND_50KM_r056_c017"] = ["Kargil (Ladakh)", "Ladakh"]
        
        with open(rev_mapping_path, "w", encoding="utf-8") as f:
            json.dump(rev_map, f, indent=2)

    print("Geographic data setup complete!")

if __name__ == "__main__":
    main()
