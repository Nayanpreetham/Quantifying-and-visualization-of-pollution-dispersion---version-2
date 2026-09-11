import cdsapi
import os
import argparse

def download_era5(year, month, output_dir):
    c = cdsapi.Client()
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f'era5_{year}_{month:02d}.nc')
    if os.path.exists(file_path):
        print(f"File {file_path} already exists. Skipping download.")
        return file_path
        
    print(f"Downloading ERA5 data for {year}-{month:02d} to {file_path}")
    
    # Required variables for India Pollution Transport Project
    variables = [
        '10m_u_component_of_wind',
        '10m_v_component_of_wind',
        '2m_temperature',
        '2m_dewpoint_temperature',
        'surface_pressure',
        'boundary_layer_height',
        'surface_sensible_heat_flux',
        'surface_latent_heat_flux',
        'total_precipitation'
    ]
    
    try:
        c.retrieve(
            'reanalysis-era5-single-levels',
            {
                'product_type': 'reanalysis',
                'variable': variables,
                'year': str(year),
                'month': f"{month:02d}",
                'day': ['01'],
                'time': [f"{i:02d}:00" for i in range(24)],
                'area': [35, 68, 6, 97],
                'format': 'netcdf'
            },
            file_path
        )
        print(f"Successfully downloaded {file_path}")
        return file_path
    except Exception as e:
        print(f"Error downloading ERA5 data: {e}")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--month', type=int, required=True)
    parser.add_argument('--out_dir', type=str, default='data/raw/era5')
    args = parser.parse_args()
    
    download_era5(args.year, args.month, args.out_dir)
