import xarray as xr
import zipfile
import io

print("=== ERA5 INSTANTANEOUS FILES COVERAGE ===")
for y in [2020, 2021, 2022, 2023]:
    fpath = f"data/raw/era5/{y}/era5_{y}_instant.nc"
    ds = xr.open_dataset(fpath)
    t = ds["valid_time" if "valid_time" in ds else "time"].values
    print(f"Year {y}: {len(t)} steps | Range: {t[0]} to {t[-1]}")
    ds.close()

# Check 2024 zip
zpath = "data/raw/era5/era5_2024.nc"
with zipfile.ZipFile(zpath, 'r') as z:
    for name in z.namelist():
        if "instant" in name:
            data = z.read(name)
            ds = xr.open_dataset(io.BytesIO(data))
            t = ds["valid_time" if "valid_time" in ds else "time"].values
            print(f"Year 2024 ({name}): {len(t)} steps | Range: {t[0]} to {t[-1]}")
            ds.close()
