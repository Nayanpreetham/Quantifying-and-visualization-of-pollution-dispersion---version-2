import xarray as xr
import os

PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
ERA5_FOLDER = os.path.join(PROJECT, "era5")
nc_file = os.path.join(ERA5_FOLDER, "era5_2020.nc")

print(f"Checking file: {nc_file}")
print(f"File exists: {os.path.exists(nc_file)}")

try:
    # Try with explicit engine
    ds = xr.open_dataset(nc_file, engine='netcdf4')
    print("✓ Successfully opened with netcdf4 engine")
    print(f"Variables: {list(ds.data_vars)}")
    ds.close()
except Exception as e:
    print(f"Error with netcdf4: {e}")
    
    try:
        # Try with h5netcdf if available
        ds = xr.open_dataset(nc_file, engine='h5netcdf')
        print("✓ Successfully opened with h5netcdf engine")
        ds.close()
    except:
        print("h5netcdf not available")
        
    try:
        # Try with scipy as last resort
        ds = xr.open_dataset(nc_file, engine='scipy')
        print("✓ Successfully opened with scipy engine")
        ds.close()
    except Exception as e:
        print(f"Error with scipy: {e}")