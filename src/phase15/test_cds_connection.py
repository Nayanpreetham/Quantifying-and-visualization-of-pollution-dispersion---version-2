"""
Test CDS API connection and authentication safely without logging credentials.
"""
import sys
import os

try:
    import cdsapi
    c = cdsapi.Client()
    print("CDS API Client initialized successfully.")
    print(f"Target URL: {c.url}")
    # Try a minimal probe request: 1 time step, 1 variable
    print("Testing connection with a minimal single-timestep probe request...")
    res = c.retrieve(
        'reanalysis-era5-single-levels',
        {
            'product_type': 'reanalysis',
            'variable': ['10m_u_component_of_wind', '10m_v_component_of_wind'],
            'year': '2019',
            'month': '01',
            'day': '01',
            'time': '00:00',
            'area': [35, 68, 6, 97],
            'format': 'netcdf'
        },
        'src/phase15/probe_test.nc'
    )
    print("Probe request completed successfully.")
    if os.path.exists('src/phase15/probe_test.nc'):
        print(f"Downloaded probe file: {os.path.getsize('src/phase15/probe_test.nc')} bytes")
        os.remove('src/phase15/probe_test.nc')
except Exception as e:
    print(f"CDS API probe failed or unavailable: {type(e).__name__}: {e}")
