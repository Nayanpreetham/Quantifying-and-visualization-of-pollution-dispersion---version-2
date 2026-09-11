import xarray as xr
import numpy as np
import os
import argparse
import zipfile

def derive_meteorology(input_file, output_dir):
    print(f"Processing ERA5 meteorology from {input_file}...")
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_file)
    out_file = os.path.join(output_dir, filename.replace('raw', 'processed').replace('.zip', '.nc'))
    
    if os.path.exists(out_file):
        print(f"File {out_file} already exists. Skipping.")
        return out_file
        
    # Check if it's a ZIP file masquerading as .nc
    is_zip = False
    with open(input_file, 'rb') as f:
        if f.read(4) == b'PK\x03\x04':
            is_zip = True
            
    if is_zip:
        print("Extracting ZIP archive...")
        extract_dir = input_file + '_extracted'
        with zipfile.ZipFile(input_file, 'r') as z:
            z.extractall(extract_dir)
            nc_files = [os.path.join(extract_dir, f) for f in z.namelist() if f.endswith('.nc')]
        
        # Merge multiple nc files
        datasets = [xr.open_dataset(f) for f in nc_files]
        ds = xr.merge(datasets)
    else:
        ds = xr.open_dataset(input_file)
    
    # Check if necessary variables exist
    required_vars = ['u10', 'v10', 't2m', 'blh', 'sshf']
    for v in required_vars:
        if v not in ds.data_vars:
            print(f"Warning: {v} not found in dataset. Filling with NaNs or placeholders.")
            if v == 'sshf':
                ds['sshf'] = ds['u10'] * 0.0 
    
    # 1. Wind Speed and Direction
    ws = np.sqrt(ds['u10']**2 + ds['v10']**2)
    wd = (270 - (180/np.pi) * np.arctan2(ds['v10'], ds['u10'])) % 360
    
    # 2. Friction velocity (u*) - Simplified neutral assumption for V1
    k = 0.4
    z = 10.0
    z0 = 0.1
    u_star = ws * k / np.log(z / z0)
    u_star = u_star.where(u_star > 0.01, 0.01)
    
    # 3. Monin-Obukhov Length (L)
    H = -ds['sshf'] if 'sshf' in ds.data_vars else ds['u10']*0.0
    H = xr.where(np.abs(H) > 0.1, H, xr.where(H >= 0, 0.1, -0.1))
    
    rho = 1.2
    cp = 1005.0
    g = 9.81
    T_v = ds['t2m']
    
    L = - (rho * cp * T_v * u_star**3) / (k * g * H)
    L = L.where(np.abs(L) < 10000, np.sign(L)*10000)
    
    # 4. Lateral Turbulence (sigma_v)
    sigma_v_unstable = u_star * np.sqrt(3.6 + 2.0 * np.power(np.abs(-z/L), 2/3))
    sigma_v_stable = u_star * 1.9
    sigma_v = xr.where(L < 0, sigma_v_unstable, sigma_v_stable)
    
    # 5. BLH
    blh = ds['blh'].where(ds['blh'] > 50.0, 50.0)
    
    # Assign new variables
    ds_out = xr.Dataset({
        'wind_speed': ws.astype(np.float32),
        'wind_direction': wd.astype(np.float32),
        'u_star': u_star.astype(np.float32),
        'L': L.astype(np.float32),
        'sigma_v': sigma_v.astype(np.float32),
        'pblh': blh.astype(np.float32),
        't2m': ds['t2m'].astype(np.float32)
    })
    
    # Add optional vars
    if 'sp' in ds.data_vars:
        ds_out['sp'] = ds['sp'].astype(np.float32)
    
    # Save as NetCDF
    print("Saving processed variables...")
    ds_out.to_netcdf(out_file)
    print(f"Saved derived meteorology to {out_file}")
    
    ds.close()
    if is_zip:
        for d in datasets:
            d.close()
            
    return out_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--out_dir', type=str, default='data/processed/era5')
    args = parser.parse_args()
    
    derive_meteorology(args.input, args.out_dir)
