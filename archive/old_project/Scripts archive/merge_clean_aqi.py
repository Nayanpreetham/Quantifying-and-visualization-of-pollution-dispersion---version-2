import pandas as pd
import glob
import os
import numpy as np

# -------- PATHS --------
AQI_FOLDER = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project\aqi_data"
OUTPUT_FOLDER = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project\output"

# -------- FIXED TIMELINE --------
full_dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")

# -------- LOAD FILES SORTED BY FILENAME --------
files = sorted(glob.glob(os.path.join(AQI_FOLDER, "*.csv")))
print(f"Found {len(files)} files")

final_list = []

for file in files:
    try:
        # Read raw
        df = pd.read_csv(file)

        # Normalize column names
        df.columns = [col.lower().strip() for col in df.columns]

        # Keep only date, city, index value
        df = df[["date", "city", "index value"]].copy()
        df.rename(columns={"index value": "aqi"}, inplace=True)

        # Get city name from filename (reliable)
        city_name = os.path.basename(file).replace("_AQIBulletins.csv", "")

        # Parse date
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
        df = df.dropna(subset=["date"])

        # AQI to numeric
        df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")

        # Remove out-of-range
        df.loc[(df["aqi"] < 0) | (df["aqi"] > 1000), "aqi"] = np.nan

        # Set date as index
        df = df.set_index("date")[["aqi"]]

        # Reindex to full 2020-2023 timeline
        df = df.reindex(full_dates)

        # Linear interpolation for internal gaps
        df["aqi"] = df["aqi"].interpolate(method="linear")

        # Fill remaining front/back edges with linear extrapolation (limited 30 days)
        df["aqi"] = df["aqi"].bfill(limit=30).ffill(limit=30)

        # Reset index
        df = df.reset_index()
        df.columns = ["date", "aqi"]
        df["city"] = city_name

        # Final column order
        df = df[["date", "city", "aqi"]]

        final_list.append(df)
        print(f"Done: {city_name} — {df['aqi'].notna().sum()} days filled")

    except Exception as e:
        print(f"ERROR in {file}: {e}")

# -------- MERGE (in filename order, no extra sorting) --------
aqi_final = pd.concat(final_list, ignore_index=True)

# Format date as dd-mm-yyyy
aqi_final["date"] = aqi_final["date"].dt.strftime("%d-%m-%Y")

print(f"\nFinal shape: {aqi_final.shape}")
print(f"Cities: {aqi_final['city'].nunique()}")

# -------- SAVE --------
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
aqi_final.to_csv(os.path.join(OUTPUT_FOLDER, "aqi_final_fixed.csv"), index=False)
print("Saved successfully!")