import zipfile
import os
import shutil

PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
ERA5_FOLDER = os.path.join(PROJECT, "era5")

print("Extracting ERA5 ZIP files...")
print("=" * 50)

for year in [2020, 2021, 2022, 2023]:
    zip_path = os.path.join(ERA5_FOLDER, f"era5_{year}.nc")
    
    if not os.path.exists(zip_path):
        print(f"⚠ File not found: era5_{year}.nc")
        continue
    
    print(f"\n📦 Processing {year}...")
    
    # Create year-specific folder
    year_folder = os.path.join(ERA5_FOLDER, str(year))
    os.makedirs(year_folder, exist_ok=True)
    
    # Extract zip contents
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(year_folder)
        print(f"  Extracted: {zf.namelist()}")
    
    # Rename the extracted files for clarity
    instant_file = os.path.join(year_folder, 'data_stream-oper_stepType-instant.nc')
    accum_file = os.path.join(year_folder, 'data_stream-oper_stepType-accum.nc')
    
    if os.path.exists(instant_file):
        new_instant = os.path.join(year_folder, f'era5_{year}_instant.nc')
        os.rename(instant_file, new_instant)
        print(f"  ✓ Renamed instant file")
    
    if os.path.exists(accum_file):
        new_accum = os.path.join(year_folder, f'era5_{year}_accum.nc')
        os.rename(accum_file, new_accum)
        print(f"  ✓ Renamed accum file")

print("\n✅ Extraction complete!")
print(f"Files extracted to: {ERA5_FOLDER}")
