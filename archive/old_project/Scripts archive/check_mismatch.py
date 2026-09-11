import pandas as pd
import os

PROJECT  = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
AQI_DATA = os.path.join(PROJECT, "aqi_data")
OUTPUT   = os.path.join(PROJECT, "output")

SEP = "=" * 65

# ================================================================
# CHECK 1 — Date format reality check on 10 sample files
# ================================================================
print(SEP)
print("CHECK 1 — Actual date format in raw files")
print(SEP)

files = sorted(os.listdir(AQI_DATA))[:10]
for fname in files:
    df = pd.read_csv(os.path.join(AQI_DATA, fname), nrows=3)
    raw_dates = df["date"].tolist()
    # Read WITHOUT any parsing to see raw string
    print(f"  {fname:<45} raw dates: {raw_dates}")

# ================================================================
# CHECK 2 — City name in filename vs city name INSIDE the file
# ================================================================
print(f"\n{SEP}")
print("CHECK 2 — Filename city vs city column inside file")
print(SEP)

print(f"  {'Filename city':<35} {'Inside city column':<35} {'Match?'}")
print(f"  {'-'*35} {'-'*35} {'-'*6}")

mismatches = []
for fname in sorted(os.listdir(AQI_DATA)):
    if not fname.endswith(".csv"):
        continue
    # City name from filename
    name_from_file = fname.replace("_AQIBulletins.csv", "").replace("_", " ")
    
    # City name from inside CSV
    df = pd.read_csv(os.path.join(AQI_DATA, fname), nrows=1)
    city_col = next((c for c in df.columns if c.strip().lower() == "city"), None)
    if city_col:
        name_inside = str(df[city_col].iloc[0]).strip()
    else:
        name_inside = "NO CITY COL"
    
    match = "✅" if name_from_file.strip() == name_inside.strip() else "❌"
    if match == "❌":
        mismatches.append((name_from_file, name_inside))
    print(f"  {name_from_file:<35} {name_inside:<35} {match}")

print(f"\n  Total mismatches: {len(mismatches)}")

# ================================================================
# CHECK 3 — City names in aqi_with_coords vs raw files
# ================================================================
print(f"\n{SEP}")
print("CHECK 3 — Cities in aqi_with_coords vs raw AQI files")
print(SEP)

coords_cities = set(pd.read_csv(os.path.join(OUTPUT, "aqi_with_coords.csv"))["city"].unique())
raw_cities    = set()
for fname in os.listdir(AQI_DATA):
    if fname.endswith(".csv"):
        df = pd.read_csv(os.path.join(AQI_DATA, fname), nrows=1)
        city_col = next((c for c in df.columns if c.strip().lower() == "city"), None)
        if city_col:
            raw_cities.add(str(df[city_col].iloc[0]).strip())

in_coords_not_raw = coords_cities - raw_cities
in_raw_not_coords = raw_cities - coords_cities

print(f"  Cities in aqi_with_coords  : {len(coords_cities)}")
print(f"  Cities in raw AQI files    : {len(raw_cities)}")
print(f"\n  In coords but NOT in raw   ({len(in_coords_not_raw)}): {sorted(in_coords_not_raw)}")
print(f"\n  In raw but NOT in coords   ({len(in_raw_not_coords)}): {sorted(in_raw_not_coords)}")

print(f"\n{SEP}")
print("  ✅ DONE — this tells us exactly where names diverge")
print(SEP)