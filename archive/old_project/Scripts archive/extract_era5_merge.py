import numpy as np
import pandas as pd
import xarray as xr
import os

# -------- PATHS --------
PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
OUTPUT_FOLDER = os.path.join(PROJECT, "output")
ERA5_FOLDER = os.path.join(PROJECT, "era5")

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------- LOAD CITY COORDINATES --------
aqi = pd.read_csv(os.path.join(OUTPUT_FOLDER, "aqi_with_coords.csv"))
aqi["date"] = pd.to_datetime(aqi["date"], format="%d-%m-%Y")

cities = aqi[["city", "lat", "lon"]].drop_duplicates().reset_index(drop=True)
print(f"Cities to extract: {len(cities)}")
print(f"Years to process: 2020-2023")
print("=" * 60)

# -------- BILINEAR INTERPOLATION FUNCTION --------
def bilinear_extract(ds_daily, lat, lon):
    return ds_daily.interp(latitude=lat, longitude=lon, method="linear")

# -------- EXTRACT EACH YEAR --------
all_era5 = []

for year in [2020, 2021, 2022, 2023]:
    year_folder = os.path.join(ERA5_FOLDER, str(year))
    instant_file = os.path.join(year_folder, f'era5_{year}_instant.nc')
    accum_file = os.path.join(year_folder, f'era5_{year}_accum.nc')
    
    if not os.path.exists(instant_file) or not os.path.exists(accum_file):
        print(f"\n⚠ Missing files for {year}, skipping...")
        continue
    
    print(f"\n📊 Processing {year}...")
    
    # Open both files
    ds_instant = xr.open_dataset(instant_file)
    ds_accum = xr.open_dataset(accum_file)
    
    # Print available variables for first year
    if year == 2020:
        print(f"\n  Instant variables: {list(ds_instant.data_vars)}")
        print(f"  Accum variables: {list(ds_accum.data_vars)}")
        print(f"  Coordinates: {list(ds_instant.coords)}")
        print(f"  Dimensions: {dict(ds_instant.sizes)}")
        print(f"  Lat range: {float(ds_instant.latitude.min()):.2f} to {float(ds_instant.latitude.max()):.2f}")
        print(f"  Lon range: {float(ds_instant.longitude.min()):.2f} to {float(ds_instant.longitude.max()):.2f}\n")
    
    # Rename valid_time to time for easier handling
    ds_instant = ds_instant.rename({'valid_time': 'time'})
    ds_accum = ds_accum.rename({'valid_time': 'time'})
    
    # Resample to daily means (instantaneous variables)
    ds_instant_daily = ds_instant.resample(time="1D").mean()
    # Resample accumulated variables (sum for precipitation)
    ds_accum_daily = ds_accum.resample(time="1D").sum()
    
    year_records = []
    
    for i, row in cities.iterrows():
        city = row["city"]
        lat = row["lat"]
        lon = row["lon"]
        
        try:
            # Extract values at city location
            point_instant = bilinear_extract(ds_instant_daily, lat, lon)
            point_accum = bilinear_extract(ds_accum_daily, lat, lon)
            
            # Prepare data dictionary
            data = {
                "date": pd.to_datetime(point_instant["time"].values),
                "city": city,
            }
            
            # Extract variables from instant file
            if "t2m" in point_instant:
                data["t2m"] = np.round(point_instant["t2m"].values - 273.15, 3)  # K to °C
            
            if "d2m" in point_instant:
                data["d2m"] = np.round(point_instant["d2m"].values - 273.15, 3)
            
            if "u10" in point_instant:
                data["u10"] = np.round(point_instant["u10"].values, 4)
            
            if "v10" in point_instant:
                data["v10"] = np.round(point_instant["v10"].values, 4)
            
            if "sp" in point_instant:
                data["sp_hpa"] = np.round(point_instant["sp"].values / 100, 2)  # Pa to hPa
            
            if "blh" in point_instant:
                data["blh"] = np.round(point_instant["blh"].values, 2)
            
            # Extract precipitation from accum file
            if "tp" in point_accum:
                data["tp_mm"] = np.round(point_accum["tp"].values * 1000, 3)  # m to mm
            
            # Calculate derived variables if u10 and v10 exist
            if "u10" in data and "v10" in data:
                data["wind_speed"] = np.sqrt(data["u10"]**2 + data["v10"]**2)
                data["wind_speed"] = np.round(data["wind_speed"], 4)
                
                data["wind_direction"] = (np.degrees(np.arctan2(data["v10"], data["u10"])) + 360) % 360
                data["wind_direction"] = np.round(data["wind_direction"], 2)
            
            # Calculate relative humidity if t2m and d2m exist
            if "t2m" in data and "d2m" in data:
                rh = 100 * (np.exp(17.625 * data["d2m"] / (243.04 + data["d2m"])) /
                           np.exp(17.625 * data["t2m"] / (243.04 + data["t2m"])))
                data["humidity_pct"] = np.round(np.clip(rh, 0, 100), 2)
            
            df = pd.DataFrame(data)
            year_records.append(df)
            
        except Exception as e:
            print(f"  Error at {city}, {year}: {e}")
            continue
        
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(cities)} cities")
    
    if year_records:
        year_df = pd.concat(year_records, ignore_index=True)
        all_era5.append(year_df)
        print(f"  ✓ {year} complete: {len(year_df)} rows")
    
    ds_instant.close()
    ds_accum.close()

# -------- COMBINE AND MERGE --------
if all_era5:
    era5_df = pd.concat(all_era5, ignore_index=True)
    era5_df = era5_df.sort_values(["city", "date"]).reset_index(drop=True)
    print(f"\n📈 Total ERA5 rows extracted: {len(era5_df)}")
    
    # Merge with AQI data
    aqi["date"] = pd.to_datetime(aqi["date"], format="%d-%m-%Y")
    era5_df["date"] = pd.to_datetime(era5_df["date"])
    
    merged = aqi.merge(era5_df, on=["city", "date"], how="left")
    merged["date"] = merged["date"].dt.strftime("%d-%m-%Y")
    
    print(f"\n📊 Final merged dataset:")
    print(f"  Shape: {merged.shape}")
    print(f"  Columns: {list(merged.columns)}")
    missing_cols = [col for col in ['t2m', 'tp_mm'] if col in merged.columns]
    if missing_cols:
        print(f"  Missing ERA5 data: {merged[missing_cols[0]].isna().sum()}")
    
    # Save result
    output_file = os.path.join(OUTPUT_FOLDER, "aqi_era5_merged.csv")
    merged.to_csv(output_file, index=False)
    print(f"\n✅ Saved to: {output_file}")
else:
    print("\n❌ No data extracted. Please check your files.")