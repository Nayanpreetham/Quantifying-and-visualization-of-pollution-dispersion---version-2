import numpy as np
import pandas as pd
import xarray as xr
import os

# -------- PATHS --------
PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
OUTPUT_FOLDER = os.path.join(PROJECT, "output")
ERA5_FOLDER = os.path.join(PROJECT, "era5")  # This was missing

# Create output folder if it doesn't exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Point to files in the era5 folder
ERA5_FILES = {
    2020: os.path.join(ERA5_FOLDER, "era5_2020.nc"),
    2021: os.path.join(ERA5_FOLDER, "era5_2021.nc"),
    2022: os.path.join(ERA5_FOLDER, "era5_2022.nc"),
    2023: os.path.join(ERA5_FOLDER, "era5_2023.nc"),
}

VARIABLES = ["t2m", "d2m", "u10", "v10", "tp", "sp", "blh"]

# -------- BILINEAR INTERPOLATION FUNCTION --------
def bilinear_extract(ds_daily, lat, lon):
    """
    Extract values at exact (lat, lon) using bilinear interpolation
    across the 4 surrounding ERA5 grid points.
    """
    result = ds_daily.interp(
        latitude=lat,
        longitude=lon,
        method="linear"          # bilinear for 2D grids
    )
    return result

# -------- LOAD CITY COORDINATES --------
aqi = pd.read_csv(os.path.join(OUTPUT_FOLDER, "aqi_with_coords.csv"))
aqi["date"] = pd.to_datetime(aqi["date"], format="%d-%m-%Y")

cities = aqi[["city", "lat", "lon"]].drop_duplicates().reset_index(drop=True)
print(f"Cities to extract: {len(cities)}")

# -------- EXTRACT ERA5 YEAR BY YEAR --------
all_era5 = []

for year, nc_file in ERA5_FILES.items():
    print(f"\nProcessing {year}...")
    ds = xr.open_dataset(nc_file )

    # Print variables once to confirm names
    if year == 2020:
        print("Variables in NC file:", list(ds.data_vars))
        print("Dimensions:", dict(ds.dims))
        print("Lat range:", float(ds.latitude.min()), "to", float(ds.latitude.max()))
        print("Lon range:", float(ds.longitude.min()), "to", float(ds.longitude.max()))

    # Resample hourly → daily mean BEFORE interpolation (much faster)
    ds_daily = ds[VARIABLES].resample(time="1D").mean()

    year_records = []

    for i, row in cities.iterrows():
        city = row["city"]
        lat  = row["lat"]
        lon  = row["lon"]

        # ---- BILINEAR INTERPOLATION at exact city coordinates ----
        point = bilinear_extract(ds_daily, lat, lon)

        # ---- PRIMARY VARIABLES ----
        t2m = point["t2m"].values - 273.15       # K → °C
        d2m = point["d2m"].values - 273.15       # K → °C
        u10 = point["u10"].values
        v10 = point["v10"].values
        tp  = point["tp"].values * 1000          # m → mm
        sp  = point["sp"].values / 100           # Pa → hPa
        blh = point["blh"].values                # metres

        # ---- DERIVED VARIABLES ----
        wind_speed     = np.sqrt(u10**2 + v10**2)
        wind_direction = (np.degrees(np.arctan2(v10, u10)) + 360) % 360

        # Relative Humidity via Magnus formula (meteorological standard)
        # Uses actual dew point depression — more accurate than simple ratio
        rh = 100 * (
            np.exp(17.625 * d2m / (243.04 + d2m)) /
            np.exp(17.625 * t2m / (243.04 + t2m))
        )
        rh = np.clip(rh, 0, 100)

        dates = pd.to_datetime(point["time"].values)

        df = pd.DataFrame({
            "date":           dates,
            "city":           city,
            "t2m":            np.round(t2m, 3),
            "d2m":            np.round(d2m, 3),
            "u10":            np.round(u10, 4),
            "v10":            np.round(v10, 4),
            "tp_mm":          np.round(tp, 4),
            "sp_hpa":         np.round(sp, 2),
            "blh":            np.round(blh, 2),
            "wind_speed":     np.round(wind_speed, 4),
            "wind_direction": np.round(wind_direction, 2),
            "humidity_pct":   np.round(rh, 2),
        })

        year_records.append(df)

        if (i + 1) % 50 == 0:
            print(f"  [{year}] {i+1}/{len(cities)} cities done...")

    year_df = pd.concat(year_records, ignore_index=True)
    all_era5.append(year_df)
    print(f"  Year {year} complete: {len(year_df)} rows")
    ds.close()

# -------- COMBINE ALL YEARS --------
era5_df = pd.concat(all_era5, ignore_index=True)
era5_df = era5_df.sort_values(["city", "date"]).reset_index(drop=True)
print(f"\nTotal ERA5 rows extracted: {era5_df.shape}")

# -------- MERGE WITH AQI --------
aqi["date"] = pd.to_datetime(aqi["date"], format="%d-%m-%Y")
era5_df["date"] = pd.to_datetime(era5_df["date"])

merged = aqi.merge(era5_df, on=["city", "date"], how="left")
merged["date"] = merged["date"].dt.strftime("%d-%m-%Y")

print(f"Final merged shape: {merged.shape}")
print(f"Columns: {list(merged.columns)}")
print(f"Rows missing ERA5 data: {merged['t2m'].isna().sum()}")

# -------- SAVE --------
merged.to_csv(os.path.join(OUTPUT_FOLDER, "aqi_era5_merged.csv"), index=False)
print("\nSaved: aqi_era5_merged.csv")