import cdsapi

c = cdsapi.Client()

year = '2024'   # change later

c.retrieve(
    'reanalysis-era5-single-levels',
    {
        'product_type': 'reanalysis',
        'variable': [
            '10m_u_component_of_wind',
            '10m_v_component_of_wind',
            '2m_temperature',
            '2m_dewpoint_temperature',
            'total_precipitation',
            'surface_pressure',
            'boundary_layer_height'
        ],
        'year': year,
        'month': [f"{i:02d}" for i in range(1, 13)],
        'day': [f"{i:02d}" for i in range(1, 32)],
        'time': ['00:00','06:00','12:00','18:00'],  # reduced size
        'area': [35, 68, 6, 97],
        'format': 'netcdf'
    },
    f'era5_{year}.nc'
)

print("Download complete")