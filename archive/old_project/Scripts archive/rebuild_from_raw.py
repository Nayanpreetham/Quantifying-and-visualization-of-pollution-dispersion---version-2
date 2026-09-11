import pandas as pd
import numpy as np
import rasterio
import os

# ================================================================
PROJECT  = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
AQI_DATA = os.path.join(PROJECT, "aqi_data")
OUTPUT   = os.path.join(PROJECT, "output")
DEM_PATH = os.path.join(PROJECT, "india_dem.tif")
ERA5_OUT = os.path.join(OUTPUT, "aqi_era5_merged.csv")
SEP = "=" * 65

# ================================================================
# STEP 1 — Read ALL raw AQI files with correct date parsing
# ================================================================
print(SEP)
print("STEP 1 — Load & normalize all raw AQI files")
print(SEP)

# Fix city names that have underscore inside the CSV column
CITY_NAME_FIX = {
    "Loni_Dehat"     : "Loni Dehat",
    "Loni_Ghaziabad" : "Loni Ghaziabad",
}

def parse_date_column(series):
    """
    Robustly parse dates regardless of format.
    If first part is 4 digits → YYYY-MM-DD, else → DD-MM-YYYY
    """
    def parse_single(val):
        val = str(val).strip()
        parts = val.replace("/", "-").split("-")
        if len(parts) != 3:
            return pd.NaT
        if len(parts[0]) == 4:          # YYYY-MM-DD
            try:
                return pd.Timestamp(f"{parts[0]}-{parts[1]}-{parts[2]}")
            except:
                return pd.NaT
        else:                           # DD-MM-YYYY
            try:
                return pd.Timestamp(f"{parts[2]}-{parts[1]}-{parts[0]}")
            except:
                return pd.NaT
    return series.apply(parse_single)

all_aqi = []
skipped = []

for fname in sorted(os.listdir(AQI_DATA)):
    if not fname.endswith(".csv"):
        continue
    fpath = os.path.join(AQI_DATA, fname)
    try:
        df = pd.read_csv(fpath)
        df.columns = df.columns.str.strip()
        df = df.rename(columns={"City": "city", "Index Value": "aqi"})
        df = df[["date", "city", "aqi"]].copy()
        df["city"] = df["city"].str.strip().replace(CITY_NAME_FIX)
        df["date"] = parse_date_column(df["date"])
        df = df[df["date"].notna()]
        df = df[(df["date"].dt.year >= 2020) & (df["date"].dt.year <= 2023)]
        if len(df) > 0:
            all_aqi.append(df)
    except Exception as e:
        skipped.append((fname, str(e)))

if skipped:
    print(f"  ⚠ Skipped: {skipped}")

aqi_raw = pd.concat(all_aqi, ignore_index=True)
aqi_raw = aqi_raw.drop_duplicates(subset=["city", "date"])
aqi_raw = aqi_raw.sort_values(["city", "date"]).reset_index(drop=True)

print(f"  ✅ Total AQI rows (2020-2023)  : {len(aqi_raw):,}")
print(f"  ✅ Cities                       : {aqi_raw['city'].nunique()}")
print(f"  ✅ Date range                   : {aqi_raw['date'].min().date()} → {aqi_raw['date'].max().date()}")
print(f"  ✅ AQI nulls                    : {aqi_raw['aqi'].isna().sum()}")

print(f"\n  Rows per year:")
for yr, grp in aqi_raw.groupby(aqi_raw["date"].dt.year):
    print(f"    {yr}: {len(grp):,} rows  |  {grp['city'].nunique()} cities")

print(f"\n  Top 10 cities by AQI readings:")
print(aqi_raw.groupby("city").size().sort_values(ascending=False).head(10).to_string())
print(f"\n  Bottom 10 cities by AQI readings:")
print(aqi_raw.groupby("city").size().sort_values(ascending=True).head(10).to_string())

# ================================================================
# STEP 2 — Attach city coordinates
# ================================================================
print(f"\n{SEP}")
print("STEP 2 — Attach city coordinates")
print(SEP)

coords = pd.read_csv(os.path.join(OUTPUT, "city_coordinates.csv"))
coords["city"] = coords["city"].str.strip()

aqi_coords = aqi_raw.merge(coords, on="city", how="left")

missing_coords = aqi_coords[aqi_coords["lat"].isna()]["city"].unique()
if len(missing_coords) > 0:
    print(f"  ⚠ Cities missing coordinates ({len(missing_coords)}): {list(missing_coords)}")
else:
    print(f"  ✅ All cities have coordinates")

aqi_coords = aqi_coords[aqi_coords["lat"].notna()].reset_index(drop=True)
print(f"  Rows after coord merge : {len(aqi_coords):,}")

# ================================================================
# STEP 3 — Merge ERA5 weather data
# ================================================================
print(f"\n{SEP}")
print("STEP 3 — Merge ERA5 weather data")
print(SEP)

era5 = pd.read_csv(ERA5_OUT)
era5["date"] = parse_date_column(era5["date"])
era5["city"] = era5["city"].str.strip().replace(CITY_NAME_FIX)

era5_cols = ["date", "city", "t2m", "d2m", "u10", "v10",
             "sp_hpa", "blh", "tp_mm", "wind_speed", "wind_direction", "humidity_pct"]
era5 = era5[era5_cols]

merged = aqi_coords.merge(era5, on=["city", "date"], how="left")

era5_nulls = merged["t2m"].isna().sum()
print(f"  ERA5 rows              : {len(era5):,}")
print(f"  After merge            : {len(merged):,} rows")
print(f"  ERA5 nulls (t2m)       : {era5_nulls:,} ({100*era5_nulls/len(merged):.1f}%)")

if era5_nulls > 0:
    unmatched = merged[merged["t2m"].isna()]["city"].unique()
    print(f"  ⚠ Cities without ERA5 match: {list(unmatched)[:10]}")

# ================================================================
# STEP 4 — Extract elevation from DEM
# ================================================================
print(f"\n{SEP}")
print("STEP 4 — Extract elevation from india_dem.tif")
print(SEP)

city_unique = merged[["city","lat","lon"]].drop_duplicates().reset_index(drop=True)
elevations = {}

with rasterio.open(DEM_PATH) as dem:
    nodata = dem.nodata
    for _, row in city_unique.iterrows():
        try:
            val = list(dem.sample([(row["lon"], row["lat"])]))[0][0]
            if (nodata is not None and val == nodata) or val < -500:
                elevations[row["city"]] = np.nan
            else:
                elevations[row["city"]] = round(float(val), 1)
        except:
            elevations[row["city"]] = np.nan

city_unique["elevation_m"] = city_unique["city"].map(elevations)

# Fallback for missing elevation
missing_elev = city_unique[city_unique["elevation_m"].isna()]
if len(missing_elev) > 0:
    known = city_unique[city_unique["elevation_m"].notna()]
    for idx, row in missing_elev.iterrows():
        dists = np.sqrt((known["lat"]-row["lat"])**2 + (known["lon"]-row["lon"])**2)
        fallback = known.loc[dists.nsmallest(5).index, "elevation_m"].mean()
        city_unique.loc[idx, "elevation_m"] = round(fallback, 1)
        print(f"  {row['city']} → fallback elevation: {fallback:.1f}m")

merged["elevation_m"] = merged["city"].map(city_unique.set_index("city")["elevation_m"])
print(f"  ✅ Elevation range: {merged['elevation_m'].min():.1f}m → {merged['elevation_m'].max():.1f}m")

# ================================================================
# STEP 5 — Derive terrain + meteorological features
# ================================================================
print(f"\n{SEP}")
print("STEP 5 — Compute all derived features")
print(SEP)

def terrain_cat(e):
    if pd.isna(e):    return "unknown"
    elif e < 100:     return "plain"
    elif e < 500:     return "plateau"
    elif e < 1500:    return "hill"
    else:             return "mountain"

merged["terrain_category"]       = merged["elevation_m"].apply(terrain_cat)
merged["elevation_pblh_ratio"]   = np.round(merged["elevation_m"] / (merged["blh"] + 1), 4)
merged["ventilation_index"]      = np.round(merged["wind_speed"] * merged["blh"], 2)
merged["stagnation_index"]       = np.round(1 / (merged["wind_speed"] * merged["blh"] + 1), 6)
merged["dispersion_potential"]   = np.round((merged["wind_speed"] * merged["blh"]) / (merged["elevation_m"] + 1), 4)
merged["terrain_blocking_score"] = np.round(merged["elevation_m"] / (merged["wind_speed"] + 0.1), 2)

print(f"  ✅ All derived features computed")

# ================================================================
# STEP 6 — Final quality check
# ================================================================
print(f"\n{SEP}")
print("STEP 6 — Final quality check")
print(SEP)

print(f"  Shape      : {merged.shape[0]:,} rows × {merged.shape[1]} cols")
print(f"  Cities     : {merged['city'].nunique()}")
print(f"  Date range : {merged['date'].min().date()} → {merged['date'].max().date()}")
print(f"  Columns    : {list(merged.columns)}")

nulls = merged.isna().sum()
null_cols = nulls[nulls > 0]
if null_cols.empty:
    print(f"\n  Nulls      : ✅ ZERO")
else:
    print(f"\n  Nulls:")
    for col, n in null_cols.items():
        print(f"    {col:<30} {n:>7,}  ({100*n/len(merged):.1f}%)")

print(f"\n  AQI : min={merged['aqi'].min():.0f}  max={merged['aqi'].max():.0f}"
      f"  mean={merged['aqi'].mean():.1f}  std={merged['aqi'].std():.1f}")

print(f"\n  Rows per year:")
for yr, grp in merged.groupby(merged["date"].dt.year):
    print(f"    {yr}: {len(grp):,} rows  |  {grp['city'].nunique()} cities")

print(f"\n  Terrain breakdown:")
print(merged["terrain_category"].value_counts().to_string())

# ================================================================
# STEP 7 — Save
# ================================================================
merged["date"] = merged["date"].dt.strftime("%d-%m-%Y")
out_path = os.path.join(OUTPUT, "aqi_final_clean.csv")
merged.to_csv(out_path, index=False)

print(f"\n{SEP}")
print(f"  ✅ SAVED → output/aqi_final_clean.csv")
print(f"     {merged.shape[0]:,} rows × {merged.shape[1]} cols")
print(SEP)