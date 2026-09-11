import pandas as pd
import os

OUTPUT_FOLDER = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project\output"

# Manually verified coordinates for all 8 missing cities
manual_coords = {
    "Bileipada":      (21.5941, 85.7707),  # Kendujhar, Odisha
    "Kunjemura":      (20.8444, 85.1511),  # Angul district, Odisha (industrial area near Angul)
    "Loni_Dehat":     (28.7583, 77.3005),  # UP, near Ghaziabad
    "Medikeri":       (12.4272, 75.7476),  # Same as Madikeri, Kodagu, Karnataka
    "Milupara":       (21.8782, 85.1843),  # Sundargarh, Odisha (near Tensa)
    "Palkalaiperur":  (10.8071, 78.6881),  # Tiruchirappalli district, Tamil Nadu
    "Suakati":        (21.5000, 85.5833),  # Kendujhar, Odisha
    "Tumidih":        (23.7167, 86.4110),  # Dhanbad/Jharkhand area (near Jorapokhar)
}

# Load existing coordinates file
coords_path = os.path.join(OUTPUT_FOLDER, "city_coordinates.csv")
coords_df = pd.read_csv(coords_path)

# Fill in the missing ones
for city, (lat, lon) in manual_coords.items():
    coords_df.loc[coords_df["city"] == city, "lat"] = lat
    coords_df.loc[coords_df["city"] == city, "lon"] = lon

# Save updated coordinates
coords_df.to_csv(coords_path, index=False)
print(f"Updated coordinates file. Missing now: {coords_df['lat'].isna().sum()}")

# Rebuild aqi_with_coords.csv with all 277 cities
aqi = pd.read_csv(os.path.join(OUTPUT_FOLDER, "aqi_final_fixed.csv"))
aqi_with_coords = aqi.merge(coords_df, on="city", how="left")
aqi_with_coords.to_csv(os.path.join(OUTPUT_FOLDER, "aqi_with_coords.csv"), index=False)

print(f"Final shape: {aqi_with_coords.shape}")
print(f"Cities with coords: {aqi_with_coords.dropna(subset=['lat']).city.nunique()} / {aqi_with_coords.city.nunique()}")
print("Saved: aqi_with_coords.csv")