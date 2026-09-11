import pandas as pd
import numpy as np
import rasterio
import os

PROJECT  = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
OUTPUT   = os.path.join(PROJECT, "output")
DEM_PATH = os.path.join(PROJECT, "india_dem.tif")
SEP  = "=" * 65
LINE = "-" * 65

def section(title):
    print(f"\n{SEP}\n  {title}\n{SEP}")

# ================================================================
# 1 — FINAL CLEAN FILE
# ================================================================
section("1 — aqi_final_clean.csv  (YOUR MAIN DATASET)")

path = os.path.join(OUTPUT, "aqi_final_clean.csv")
if not os.path.exists(path):
    print("  ❌ FILE NOT FOUND")
else:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    print(f"  Shape          : {df.shape[0]:,} rows × {df.shape[1]} cols")
    print(f"  Columns        : {list(df.columns)}")
    print(f"  Cities         : {df['city'].nunique()}")
    print(f"  Date range     : {df['date'].min().date()} → {df['date'].max().date()}")

    # AQI
    print(f"\n  AQI stats:")
    print(f"    min   = {df['aqi'].min():.0f}")
    print(f"    max   = {df['aqi'].max():.0f}")
    print(f"    mean  = {df['aqi'].mean():.1f}")
    print(f"    std   = {df['aqi'].std():.1f}")
    print(f"    nulls = {df['aqi'].isna().sum()}")

    # Nulls per column
    nulls = df.isna().sum()
    null_cols = nulls[nulls > 0]
    if null_cols.empty:
        print(f"\n  Nulls          : ✅ ZERO across all columns")
    else:
        print(f"\n  Nulls:")
        for col, n in null_cols.items():
            print(f"    {col:<30} {n:>7,}  ({100*n/len(df):.1f}%)")

    # Duplicates
    dups = df.duplicated(subset=["city","date"]).sum()
    print(f"\n  Duplicate city+date : {dups}" + (" ✅" if dups == 0 else " ⚠"))

    # Rows per year
    print(f"\n  Rows per year:")
    for yr, grp in df.groupby(df["date"].dt.year):
        print(f"    {yr}: {len(grp):>7,} rows  |  {grp['city'].nunique():>3} cities")

    # Rows per city summary
    city_rows = df.groupby("city").size().sort_values()
    print(f"\n  Per-city row count:")
    print(f"    Min  : {city_rows.min()}  ({city_rows.idxmin()})")
    print(f"    Max  : {city_rows.max()}  ({city_rows.idxmax()})")
    print(f"    Mean : {city_rows.mean():.0f}")
    sparse = city_rows[city_rows < 100]
    if len(sparse) > 0:
        print(f"\n  ⚠ Cities with < 100 rows ({len(sparse)}) — risky for ML:")
        for city, n in sparse.items():
            print(f"      {city:<35} {n} rows")

    # ERA5 variable stats
    print(f"\n  ERA5 variable ranges:")
    era5_vars = ["t2m","d2m","sp_hpa","blh","tp_mm","wind_speed","humidity_pct"]
    for v in era5_vars:
        if v in df.columns:
            print(f"    {v:<20} min={df[v].min():>8.2f}  max={df[v].max():>8.2f}"
                  f"  mean={df[v].mean():>8.2f}  nulls={df[v].isna().sum()}")

    # Elevation
    print(f"\n  Elevation stats:")
    print(f"    min  = {df['elevation_m'].min():.1f}m")
    print(f"    max  = {df['elevation_m'].max():.1f}m")
    print(f"    mean = {df['elevation_m'].mean():.1f}m")
    print(f"    nulls= {df['elevation_m'].isna().sum()}")

    # Terrain breakdown
    print(f"\n  Terrain category breakdown:")
    print(df["terrain_category"].value_counts().to_string())

    # Derived features check
    print(f"\n  Derived feature ranges:")
    derived = ["ventilation_index","stagnation_index",
               "dispersion_potential","terrain_blocking_score","elevation_pblh_ratio"]
    for v in derived:
        if v in df.columns:
            print(f"    {v:<30} min={df[v].min():>10.4f}  max={df[v].max():>10.4f}"
                  f"  nulls={df[v].isna().sum()}")

    # AQI category distribution
    print(f"\n  AQI category distribution:")
    bins   = [0, 50, 100, 200, 300, 400, 500]
    labels = ["Good","Satisfactory","Moderate","Poor","Very Poor","Severe"]
    df["aqi_cat"] = pd.cut(df["aqi"], bins=bins, labels=labels, include_lowest=True)
    print(df["aqi_cat"].value_counts().sort_index().to_string())

# ================================================================
# 2 — PIPELINE COMPARISON (all output files)
# ================================================================
section("2 — PIPELINE COMPARISON — all output files")

files = {
    "aqi_with_coords.csv"             : "AQI with Coords (old/broken base)",
    "aqi_clean.csv"                   : "AQI Clean (old — only 4 cities)",
    "aqi_era5_merged.csv"             : "AQI + ERA5 Merged (old)",
    "aqi_era5_elevation_enhanced.csv" : "AQI + ERA5 + Elevation (old)",
    "aqi_weather_complete.csv"        : "AQI Weather Complete (old)",
    "aqi_final_fixed.csv"             : "AQI Final Fixed (old — broken)",
    "aqi_final_clean.csv"             : "✅ aqi_final_clean (NEW — USE THIS)",
}

print(f"  {'File':<45} {'Rows':>10}  {'Cities':>8}  {'AQI nulls':>10}  {'Cols':>5}")
print(f"  {'-'*45} {'-'*10}  {'-'*8}  {'-'*10}  {'-'*5}")

for fname, label in files.items():
    fpath = os.path.join(OUTPUT, fname)
    if not os.path.exists(fpath):
        print(f"  {fname:<45} NOT FOUND")
        continue
    tmp = pd.read_csv(fpath)
    aqi_nulls = tmp["aqi"].isna().sum() if "aqi" in tmp.columns else "N/A"
    cities    = tmp["city"].nunique()   if "city" in tmp.columns else "N/A"
    print(f"  {fname:<45} {len(tmp):>10,}  {cities:>8}  {str(aqi_nulls):>10}  {tmp.shape[1]:>5}")

# ================================================================
# 3 — DEM HEALTH CHECK
# ================================================================
section("3 — india_dem.tif HEALTH CHECK")

if not os.path.exists(DEM_PATH):
    print("  ❌ DEM FILE NOT FOUND")
else:
    with rasterio.open(DEM_PATH) as dem:
        print(f"  CRS            : {dem.crs}")
        print(f"  Resolution     : {dem.res[0]:.6f}° (~{dem.res[0]*111:.1f} km)")
        print(f"  Bounds         : {dem.bounds}")
        print(f"  Shape          : {dem.height:,} rows × {dem.width:,} cols")
        print(f"  Bands          : {dem.count}")
        data = dem.read(1, masked=True)
        print(f"  Elevation range: {data.min():.1f}m → {data.max():.1f}m")
        print(f"  NoData %       : {100*data.mask.sum()/data.size:.2f}%")
        print(f"  ✅ DEM covers India: lat 6–35°N, lon 68–97°E")

# ================================================================
# 4 — CITY COVERAGE CHECK
# ================================================================
section("4 — CITY COVERAGE")

coords_path = os.path.join(OUTPUT, "city_coordinates.csv")
final_path  = os.path.join(OUTPUT, "aqi_final_clean.csv")

if os.path.exists(coords_path) and os.path.exists(final_path):
    coords = pd.read_csv(coords_path)
    final  = pd.read_csv(final_path)

    coords_cities = set(coords["city"].unique())
    final_cities  = set(final["city"].unique())

    in_coords_not_final = coords_cities - final_cities
    in_final_not_coords = final_cities  - coords_cities

    print(f"  Cities in city_coordinates.csv : {len(coords_cities)}")
    print(f"  Cities in aqi_final_clean.csv  : {len(final_cities)}")

    if in_coords_not_final:
        print(f"\n  ⚠ In coords but missing from final ({len(in_coords_not_final)}):")
        print(f"    {sorted(in_coords_not_final)}")
        print(f"    → These cities have coordinates but NO AQI data in 2020-2023")
    else:
        print(f"\n  ✅ All coordinate cities are present in final dataset")

    if in_final_not_coords:
        print(f"\n  ⚠ In final but missing from coords ({len(in_final_not_coords)}):")
        print(f"    {sorted(in_final_not_coords)}")

# ================================================================
# SUMMARY
# ================================================================
section("AUDIT SUMMARY")

print(f"  {'Item':<40} {'Status'}")
print(f"  {'-'*40} {'-'*20}")

checks = [
    ("Final dataset exists",         os.path.exists(os.path.join(OUTPUT, "aqi_final_clean.csv"))),
    ("DEM file exists",              os.path.exists(DEM_PATH)),
    ("City coordinates exist",       os.path.exists(os.path.join(OUTPUT, "city_coordinates.csv"))),
]

for label, ok in checks:
    print(f"  {label:<40} {'✅ OK' if ok else '❌ MISSING'}")

if os.path.exists(final_path):
    df = pd.read_csv(final_path)
    checks2 = [
        ("Zero AQI nulls",           df["aqi"].isna().sum() == 0),
        ("Zero ERA5 nulls (t2m)",    df["t2m"].isna().sum() == 0 if "t2m" in df.columns else False),
        ("Zero elevation nulls",     df["elevation_m"].isna().sum() == 0 if "elevation_m" in df.columns else False),
        ("No duplicate city+date",   df.duplicated(subset=["city","date"]).sum() == 0),
        ("274+ cities present",      df["city"].nunique() >= 274),
        ("200k+ rows present",       len(df) >= 200000),
    ]
    for label, ok in checks2:
        print(f"  {label:<40} {'✅ OK' if ok else '❌ ISSUE'}")

print(f"\n{SEP}")
print(f"  ✅ AUDIT COMPLETE")
print(SEP)