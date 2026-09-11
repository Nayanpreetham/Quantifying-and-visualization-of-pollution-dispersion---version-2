import pandas as pd
import numpy as np
import os

PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
OUTPUT  = os.path.join(PROJECT, "output")
AQI_DATA = os.path.join(PROJECT, "aqi_data")

SEP = "=" * 65

# ================================================================
# STEP 1 — Inspect RAW AQI source files
# ================================================================
print(SEP)
print("STEP 1 — RAW AQI SOURCE FILES")
print(SEP)

if os.path.exists(AQI_DATA):
    files = os.listdir(AQI_DATA)
    print(f"  Files in aqi_data/: {files}\n")
    for f in files[:5]:  # show first 5
        fpath = os.path.join(AQI_DATA, f)
        try:
            df = pd.read_csv(fpath)
            print(f"  📄 {f}")
            print(f"     Shape   : {df.shape}")
            print(f"     Columns : {list(df.columns)}")
            print(f"     Head    :")
            print(df.head(3).to_string(index=False))
            print(f"     Nulls   : {df.isna().sum().to_dict()}")
            print()
        except Exception as e:
            print(f"  ⚠ Could not read {f}: {e}")
else:
    print("  ⚠ aqi_data folder not found!")

# ================================================================
# STEP 2 — Inspect aqi_with_coords.csv closely
# ================================================================
print(SEP)
print("STEP 2 — aqi_with_coords.csv DEEP INSPECTION")
print(SEP)

coords_path = os.path.join(OUTPUT, "aqi_with_coords.csv")
df_coords = pd.read_csv(coords_path)

print(f"  Shape        : {df_coords.shape}")
print(f"  Columns      : {list(df_coords.columns)}")
print(f"  Dtypes       :\n{df_coords.dtypes}")
print(f"\n  First 5 rows :")
print(df_coords.head(5).to_string(index=False))
print(f"\n  AQI null count : {df_coords['aqi'].isna().sum():,}")
print(f"  AQI non-null   : {df_coords['aqi'].notna().sum():,}")

# Check date column format
print(f"\n  Date samples   : {df_coords['date'].head(10).tolist()}")

# Check per-city AQI availability
city_aqi = df_coords.groupby("city")["aqi"].agg(
    total="count",
    non_null=lambda x: x.notna().sum(),
    null=lambda x: x.isna().sum()
)
city_aqi["coverage_%"] = (city_aqi["non_null"] / city_aqi["total"] * 100).round(1)
city_aqi = city_aqi.sort_values("non_null", ascending=False)

print(f"\n  Per-city AQI coverage (top 20 and bottom 20):")
print(f"  {'City':<30} {'Total':>8} {'Non-null':>10} {'Null':>8} {'Cover%':>8}")
print(f"  {'-'*30} {'-'*8} {'-'*10} {'-'*8} {'-'*8}")
for city, row in city_aqi.head(20).iterrows():
    print(f"  {city:<30} {int(row['total']):>8} {int(row['non_null']):>10} {int(row['null']):>8} {row['coverage_%']:>7.1f}%")
print("  ...")
for city, row in city_aqi.tail(20).iterrows():
    print(f"  {city:<30} {int(row['total']):>8} {int(row['non_null']):>10} {int(row['null']):>8} {row['coverage_%']:>7.1f}%")

# ================================================================
# STEP 3 — Check aqi_era5_merged date format vs aqi_with_coords
# ================================================================
print(f"\n{SEP}")
print("STEP 3 — DATE FORMAT MISMATCH CHECK")
print(SEP)

merged_path = os.path.join(OUTPUT, "aqi_era5_merged.csv")
df_merged = pd.read_csv(merged_path)

print(f"  aqi_with_coords date sample : {df_coords['date'].head(5).tolist()}")
print(f"  aqi_era5_merged date sample : {df_merged['date'].head(5).tolist()}")
print(f"  aqi_with_coords date dtype  : {df_coords['date'].dtype}")
print(f"  aqi_era5_merged date dtype  : {df_merged['date'].dtype}")

# Try to find rows that SHOULD match but don't
# Pick a city that has AQI readings
sample_city = df_coords[df_coords['aqi'].notna()]['city'].iloc[0]
print(f"\n  Sample city with AQI: '{sample_city}'")

coords_city = df_coords[df_coords['city'] == sample_city][['date','city','aqi']].head(5)
merged_city = df_merged[df_merged['city'] == sample_city][['date','city','aqi']].head(5)

print(f"\n  aqi_with_coords rows for {sample_city}:")
print(coords_city.to_string(index=False))
print(f"\n  aqi_era5_merged rows for {sample_city}:")
print(merged_city.to_string(index=False))

# ================================================================
# STEP 4 — Check what the original aqi_clean had
# ================================================================
print(f"\n{SEP}")
print("STEP 4 — aqi_clean.csv — only 4 cities, WHY?")
print(SEP)

clean_path = os.path.join(OUTPUT, "aqi_clean.csv")
df_clean = pd.read_csv(clean_path)
print(f"  Cities in aqi_clean : {sorted(df_clean['city'].unique().tolist())}")
print(f"  Shape               : {df_clean.shape}")
print(f"  Columns             : {list(df_clean.columns)}")
print(f"  Date samples        : {df_clean['date'].head(5).tolist()}")
print(f"  AQI nulls           : {df_clean['aqi'].isna().sum()}")

# ================================================================
# STEP 5 — Figure out true AQI row counts from raw
# ================================================================
print(f"\n{SEP}")
print("STEP 5 — TRUE AQI DATA AVAILABILITY SUMMARY")
print(SEP)

total_slots   = len(df_coords)
actual_aqi    = df_coords['aqi'].notna().sum()
cities        = df_coords['city'].nunique()
dates         = df_coords['date'].nunique()

print(f"  Total city-date slots  : {total_slots:,}")
print(f"  Actual AQI readings    : {actual_aqi:,}")
print(f"  Missing AQI            : {total_slots - actual_aqi:,} ({100*(total_slots-actual_aqi)/total_slots:.1f}%)")
print(f"  Cities                 : {cities}")
print(f"  Unique dates           : {dates}")
print(f"  Expected (277×1461)    : {277*1461:,}")
print(f"\n  → If actual AQI is only {actual_aqi:,}, your SOURCE data is sparse")
print(f"    meaning the raw AQI files themselves don't have daily data for all cities")
print(f"    OR the merge that created aqi_with_coords dropped data via key mismatch")

print(f"\n{SEP}")
print("  ✅ DIAGNOSTIC COMPLETE — paste output to identify root cause")
print(SEP)