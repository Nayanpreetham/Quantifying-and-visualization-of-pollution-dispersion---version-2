import xarray as xr

ds = xr.open_dataset("era5/era5_2020.nc", engine="cfgrib")
print(ds)