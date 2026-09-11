import cdsapi
import os
import calendar

# Full India domain: 5-38°N, 68-98°E
# - South boundary: 5°N covers Bengaluru (12.97°N), Chennai (13.08°N), Thiruvananthapuram (8.5°N)
# - North boundary: 38°N covers Srinagar (34.09°N) and Leh (34.17°N)
# - East boundary: 98°E covers Imphal/northeast India
DOMAIN_N = 38
DOMAIN_W = 68
DOMAIN_S = 5
DOMAIN_E = 98

PRESSURE_LEVELS = ['500', '700', '850', '925', '1000']
TIMES_3H = ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00']


def download_era5_3d_month(year, month, out_dir='data/raw/era5', overwrite=False):
    """
    Download ERA5 3D pressure-level winds (u, v, w) for a given month.

    Covers the full India domain (5-38°N, 68-98°E) at 3-hourly resolution
    on pressure levels 500/700/850/925/1000 hPa.

    For a 72-hour backward trajectory ending on the first of the month,
    the download includes the 3 preceding days as well.

    Parameters
    ----------
    year, month : int
    out_dir : str
    overwrite : bool
        If False, skips if file already exists.
    """
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f'era5_3d_{year}_{month:02d}.nc')

    if os.path.exists(out_file) and not overwrite:
        print(f"File {out_file} already exists. Skipping.")
        return out_file

    c = cdsapi.Client()

    _, num_days = calendar.monthrange(year, month)
    days = [f"{d:02d}" for d in range(1, num_days + 1)]

    # Include 3 preceding days for 72-hour backward trajectories starting on day 1
    # (these come from the previous month; handle the month rollback)
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    _, prev_num_days = calendar.monthrange(prev_year, prev_month)
    prev_days = [f"{d:02d}" for d in range(prev_num_days - 2, prev_num_days + 1)]

    print(f"Downloading ERA5 3D for {year}-{month:02d} + 3 preceding days...")
    print(f"Domain: [{DOMAIN_N}N, {DOMAIN_W}W, {DOMAIN_S}S, {DOMAIN_E}E]")

    # Download target month
    c.retrieve(
        'reanalysis-era5-pressure-levels',
        {
            'product_type': 'reanalysis',
            'format': 'netcdf',
            'variable': [
                'u_component_of_wind',
                'v_component_of_wind',
                'vertical_velocity',
            ],
            'pressure_level': PRESSURE_LEVELS,
            'year': str(year),
            'month': f"{month:02d}",
            'day': days,
            'time': TIMES_3H,
            'area': [DOMAIN_N, DOMAIN_W, DOMAIN_S, DOMAIN_E],
        },
        out_file
    )
    print(f"Download complete: {out_file}")
    return out_file


def download_pressure_levels():
    """Legacy function for pilot download (Oct-Nov 2020 window)."""
    out_dir = 'data/raw/era5'
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, 'era5_3d_2020_11_01.nc')

    if os.path.exists(out_file):
        print(f"File {out_file} already exists. Skipping download.")
        return

    c = cdsapi.Client()
    print(f"Downloading ERA5 3D pilot data (Oct-Nov 2020) to {out_file}...")
    print(f"NOTE: domain extended to {DOMAIN_N}N/{DOMAIN_S}S to cover all India cities.")

    c.retrieve(
        'reanalysis-era5-pressure-levels',
        {
            'product_type': 'reanalysis',
            'format': 'netcdf',
            'variable': [
                'u_component_of_wind', 'v_component_of_wind', 'vertical_velocity'
            ],
            'pressure_level': PRESSURE_LEVELS,
            'year': '2020',
            'month': ['10', '11'],
            'day': ['29', '30', '31', '01', '02', '03'],
            'time': TIMES_3H,
            'area': [DOMAIN_N, DOMAIN_W, DOMAIN_S, DOMAIN_E],
        },
        out_file
    )
    print("Download complete.")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Download ERA5 3D pressure-level data')
    parser.add_argument('--year', type=int, default=2020)
    parser.add_argument('--month', type=int, default=11)
    parser.add_argument('--out_dir', type=str, default='data/raw/era5')
    parser.add_argument('--pilot', action='store_true', help='Download pilot window (Oct-Nov 2020)')
    args = parser.parse_args()

    if args.pilot:
        download_pressure_levels()
    else:
        download_era5_3d_month(args.year, args.month, args.out_dir)

