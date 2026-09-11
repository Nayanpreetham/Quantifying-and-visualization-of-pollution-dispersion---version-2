import xarray as xr
import glob

# Load all nc files
files = sorted(glob.glob("../era5/*.nc"))

print("Files found:", files)

datasets = []

for f in files:
    print(f"opening {f}")
    ds = xr.open_dataset(f , engine = "netcdf4")
    datasets.append(ds)

# Merge along time dimension
combined = xr.concat(datasets, dim="time")

print("merged successfully")

# Save merged file
combined.to_netcdf("../output/era5_merged.nc")

print("Saved: era5_merged.nc")