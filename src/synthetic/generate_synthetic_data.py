"""
SYNTHETIC DATA GENERATOR — PIPELINE / CONSTRAINT VERIFICATION ONLY
===================================================================
Generates a small, clean, physically consistent 2D synthetic dataset for 10 Indian cities:
1. Delhi
2. Mumbai
3. Lucknow
4. Varanasi
5. Jaipur
6. Ahmedabad
7. Kolkata
8. Hyderabad
9. Bengaluru
10. Chennai

Output Directory: data/synthetic/
Files created:
- cities.csv
- grid.csv
- pollution.csv
- era5_wind.csv
"""

import os
import numpy as np
import pandas as pd

# Fixed seed for perfect reproducibility
NP_SEED = 42
np.random.seed(NP_SEED)

DISCLAIMER = "SYNTHETIC DATA — PIPELINE/CONSTRAINT VERIFICATION ONLY"

CITIES_DATA = [
    {"city_id": "DEL", "name": "Delhi",     "lat": 28.6139, "lon": 77.2090, "base_pm25": 180.0},
    {"city_id": "BOM", "name": "Mumbai",    "lat": 19.0760, "lon": 72.8777, "base_pm25": 90.0},
    {"city_id": "LKO", "name": "Lucknow",   "lat": 26.8467, "lon": 80.9462, "base_pm25": 160.0},
    {"city_id": "VNS", "name": "Varanasi",  "lat": 25.3176, "lon": 82.9739, "base_pm25": 150.0},
    {"city_id": "JAI", "name": "Jaipur",    "lat": 26.9124, "lon": 75.7873, "base_pm25": 110.0},
    {"city_id": "AMD", "name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714, "base_pm25": 105.0},
    {"city_id": "CCU", "name": "Kolkata",   "lat": 22.5726, "lon": 88.3639, "base_pm25": 130.0},
    {"city_id": "HYD", "name": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "base_pm25": 75.0},
    {"city_id": "BLR", "name": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "base_pm25": 45.0},
    {"city_id": "MAA", "name": "Chennai",   "lat": 13.0827, "lon": 80.2707, "base_pm25": 55.0},
]

GRID_DIM = 7        # 7x7 grid per city = 49 cells per city (490 total)
GRID_SPACING = 0.1  # 0.1 degree (~11 km spacing)
TIME_STEPS = 12     # 12 hourly steps (0 to 11h)


def generate_cities_csv(output_dir):
    df = pd.DataFrame(CITIES_DATA)
    df["data_label"] = DISCLAIMER
    path = os.path.join(output_dir, "cities.csv")
    df.to_csv(path, index=False)
    print(f"[Synthetic Generator] Saved: {path} ({len(df)} cities)")
    return df


def generate_grid_csv(cities_df, output_dir):
    grid_rows = []
    half_grid = GRID_DIM // 2

    for _, c in cities_df.iterrows():
        c_lat, c_lon = c["lat"], c["lon"]
        c_id = c["city_id"]
        c_name = c["name"]

        for r in range(GRID_DIM):
            for col in range(GRID_DIM):
                row_idx = r - half_grid
                col_idx = col - half_grid

                lat = round(c_lat + row_idx * GRID_SPACING, 4)
                lon = round(c_lon + col_idx * GRID_SPACING, 4)
                grid_id = f"{c_id}_r{r}_c{col}"
                is_center = (r == half_grid and col == half_grid)

                grid_rows.append({
                    "grid_id": grid_id,
                    "city_id": c_id,
                    "city_name": c_name,
                    "row": r,
                    "column": col,
                    "latitude": lat,
                    "longitude": lon,
                    "is_city_center": is_center,
                    "data_label": DISCLAIMER
                })

    df_grid = pd.DataFrame(grid_rows)
    path = os.path.join(output_dir, "grid.csv")
    df_grid.to_csv(path, index=False)
    print(f"[Synthetic Generator] Saved: {path} ({len(df_grid)} grid cells)")
    return df_grid


def generate_era5_wind_csv(grid_df, output_dir):
    wind_rows = []

    # Dominant wind direction for each city (meteorological convention in degrees)
    # North-westerly for IGP, Westerly/South-westerly for coastal/south
    city_wind_dirs = {
        "DEL": 315.0, "LKO": 300.0, "VNS": 290.0, "JAI": 320.0,
        "BOM": 250.0, "AMD": 270.0, "CCU": 220.0,
        "HYD": 240.0, "BLR": 250.0, "MAA": 110.0
    }

    for hour in range(TIME_STEPS):
        time_factor = np.sin(2 * np.pi * hour / 24.0)

        for _, g in grid_df.iterrows():
            c_id = g["city_id"]
            base_dir = city_wind_dirs.get(c_id, 270.0)

            # Spatial & temporal variation
            dir_var = 15.0 * np.sin(g["row"] * 0.5 + hour * 0.3)
            curr_dir_deg = (base_dir + dir_var + time_factor * 10.0) % 360.0

            # Base wind speed: 3.0 - 7.0 m/s with spatial & temporal gradient
            base_speed = 4.5 + 1.5 * np.cos(hour * np.pi / 6.0) + 0.3 * (g["row"] - g["column"])
            wind_speed = max(1.0, float(round(base_speed, 2)))

            # Mathematical conversion: direction wind comes FROM to U,V vectors going TO
            # U = -speed * sin(rad), V = -speed * cos(rad)
            rad = np.radians(curr_dir_deg)
            u10 = round(-wind_speed * np.sin(rad), 3)
            v10 = round(-wind_speed * np.cos(rad), 3)

            # Re-verify wind speed consistency
            calc_speed = round(float(np.sqrt(u10**2 + v10**2)), 2)

            wind_rows.append({
                "timestamp_hour": hour,
                "grid_id": g["grid_id"],
                "city_id": c_id,
                "latitude": g["latitude"],
                "longitude": g["longitude"],
                "u10": u10,
                "v10": v10,
                "wind_speed": calc_speed,
                "wind_direction_deg": round(curr_dir_deg, 1),
                "data_label": DISCLAIMER
            })

    df_wind = pd.DataFrame(wind_rows)
    path = os.path.join(output_dir, "era5_wind.csv")
    df_wind.to_csv(path, index=False)
    print(f"[Synthetic Generator] Saved: {path} ({len(df_wind)} wind records)")
    return df_wind


def generate_openaq_pollution_csv(grid_df, output_dir):
    pollution_rows = []

    # Map city base PM2.5
    city_pm25 = {
        "DEL": 180.0, "LKO": 160.0, "VNS": 150.0, "JAI": 110.0, "AMD": 105.0,
        "CCU": 130.0, "BOM": 90.0,  "HYD": 75.0,  "MAA": 55.0,  "BLR": 45.0
    }

    for hour in range(TIME_STEPS):
        # Diurnal multiplier (peak in morning/night, lower in afternoon)
        diurnal_mult = 1.0 + 0.25 * np.cos(2 * np.pi * (hour - 8) / 24.0)

        for _, g in grid_df.iterrows():
            c_id = g["city_id"]
            base = city_pm25[c_id]

            # Center grid has higher pollution load (urban core)
            dist_from_center = np.sqrt((g["row"] - 3)**2 + (g["column"] - 3)**2)
            spatial_mult = 1.0 - 0.08 * dist_from_center

            pm25_val = round(base * diurnal_mult * spatial_mult + np.random.normal(0, 3.0), 2)
            pm25_val = max(10.0, pm25_val)

            # Synthetic AQI conversion indicator (for pipeline testing only)
            aqi_val = int(pm25_val * 1.3)

            pollution_rows.append({
                "timestamp_hour": hour,
                "grid_id": g["grid_id"],
                "city_id": c_id,
                "city_name": g["city_name"],
                "pm25_concentration": pm25_val,
                "synthetic_aqi": aqi_val,
                "is_source_candidate": g["is_city_center"],
                "data_label": DISCLAIMER
            })

    df_pol = pd.DataFrame(pollution_rows)
    path = os.path.join(output_dir, "pollution.csv")
    df_pol.to_csv(path, index=False)
    print(f"[Synthetic Generator] Saved: {path} ({len(df_pol)} pollution records)")
    return df_pol


def run_generator(output_dir="data/synthetic"):
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n=======================================================")
    print(f"GENERATING SYNTHETIC DATA DATASETS ({DISCLAIMER})")
    print(f"=======================================================\n")

    cities = generate_cities_csv(output_dir)
    grid = generate_grid_csv(cities, output_dir)
    generate_era5_wind_csv(grid, output_dir)
    generate_openaq_pollution_csv(grid, output_dir)

    print(f"\n[Synthetic Generator] Generation Complete!\n")


if __name__ == "__main__":
    run_generator()
