"""
Extract meteorological variables from ERA5 NetCDF files.
If year > 2023, forecast using linear trend from 2020-2023.
"""

import xarray as xr
import numpy as np
import os
import glob
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

ERA5_DIR = "Raw data/era5"

def find_era5_file(year, file_type='instant'):
    """Find ERA5 NetCDF file for a given year (only for 2020-2023)."""
    if year > 2023:
        return None
    patterns = [
        f"{ERA5_DIR}/{year}/era5_{year}_{file_type}.nc",
        f"{ERA5_DIR}/{year}/data_stream-oper_stepType-{file_type}.nc",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None

def calculate_relative_humidity(t2m_k, d2m_k):
    """Calculate relative humidity from temperature and dewpoint."""
    t2m_c = t2m_k - 273.15
    d2m_c = d2m_k - 273.15
    es_t = 6.112 * np.exp((17.67 * t2m_c) / (t2m_c + 243.5))
    e_d = 6.112 * np.exp((17.67 * d2m_c) / (d2m_c + 243.5))
    rh = 100.0 * (e_d / es_t)
    return np.clip(rh, 0, 100)

def get_historical_monthly_averages(lat, lon, month, years=[2020,2021,2022,2023]):
    """
    Extract monthly average meteorology for each historical year.
    Returns dict of variable -> list of values (same order as years).
    """
    results = {var: [] for var in ['t2m', 'humidity_pct', 'u10', 'v10', 'wind_speed', 'sp_hpa', 'blh', 'tp_mm']}
    valid_years = []

    for year in years:
        nc_file_instant = find_era5_file(year, 'instant')
        if not nc_file_instant:
            continue
        ds_instant = xr.open_dataset(nc_file_instant)
        ds_point = ds_instant.sel(latitude=lat, longitude=lon, method='nearest')
        ds_month = ds_point.sel(valid_time=ds_point.valid_time.dt.month == month)
        if len(ds_month.valid_time) == 0:
            ds_instant.close()
            continue

        # Temperature
        t2m_k = float(ds_month['t2m'].mean().values)
        results['t2m'].append(t2m_k - 273.15)
        # Dewpoint and humidity
        d2m_k = float(ds_month['d2m'].mean().values)
        results['humidity_pct'].append(float(calculate_relative_humidity(t2m_k, d2m_k)))
        # Wind
        u10 = float(ds_month['u10'].mean().values)
        v10 = float(ds_month['v10'].mean().values)
        results['u10'].append(u10)
        results['v10'].append(v10)
        results['wind_speed'].append(np.sqrt(u10**2 + v10**2))
        # Pressure
        results['sp_hpa'].append(float(ds_month['sp'].mean().values) / 100.0)
        # BLH
        results['blh'].append(float(ds_month['blh'].mean().values))
        ds_instant.close()

        # Precipitation from accum file
        nc_file_accum = find_era5_file(year, 'accum')
        if nc_file_accum:
            ds_accum = xr.open_dataset(nc_file_accum)
            ds_point_accum = ds_accum.sel(latitude=lat, longitude=lon, method='nearest')
            ds_month_accum = ds_point_accum.sel(valid_time=ds_point_accum.valid_time.dt.month == month)
            if len(ds_month_accum.valid_time) > 0:
                tp_mm = float(ds_month_accum['tp'].sum().values) * 1000.0
                results['tp_mm'].append(tp_mm)
            else:
                results['tp_mm'].append(0.0)
            ds_accum.close()
        else:
            results['tp_mm'].append(0.0)

        valid_years.append(year)

    if len(valid_years) == 0:
        raise ValueError(f"No historical data for lat={lat}, lon={lon}, month={month}")

    # Convert to numpy arrays
    for var in results:
        results[var] = np.array(results[var])
    return results, np.array(valid_years)

def forecast_for_year(lat, lon, month, target_year, historical_years=[2020,2021,2022,2023]):
    """Use linear trend on historical data to forecast meteorology for target_year."""
    hist_data, years = get_historical_monthly_averages(lat, lon, month, historical_years)
    X = years.reshape(-1, 1)
    forecast = {}
    for var in hist_data:
        y = hist_data[var]
        if len(y) < 2:
            forecast[var] = y[0]  # fallback
        else:
            model = LinearRegression()
            model.fit(X, y)
            pred = model.predict([[target_year]])[0]
            forecast[var] = max(pred, 0) if var in ['tp_mm', 'wind_speed'] else pred
    return forecast

def get_monthly_climatology(lat, lon, month, year=2023):
    """
    Get monthly average meteorology.
    If year > 2023, forecast using trend.
    """
    if year <= 2023:
        nc_file_instant = find_era5_file(year, 'instant')
        if not nc_file_instant:
            raise FileNotFoundError(f"No ERA5 instant file found for year {year}")
        # Use original direct reading code (as before) - I'll keep it short here
        # But for brevity, we'll reuse the forecasting method for all years >2023
        # For years <=2023, we read directly.
        # However, to avoid duplication, we can just call the forecast function for year >2023
        # For years <=2023, we can read directly. Let me implement the direct reading quickly.
        # Since the original code worked, I'll assume direct reading works for <=2023.
        # But to save space, I'll provide a compact version that works for both.
        # Actually, the original fetch_meteo.py already worked for 2020-2023.
        # So we only need to modify the part for year > 2023.
        # I'll rewrite the function completely.
        pass

    # For simplicity, I'll implement the full logic here:
    if year <= 2023:
        # Original direct reading (same as before)
        nc_file_instant = find_era5_file(year, 'instant')
        if not nc_file_instant:
            raise FileNotFoundError(f"No ERA5 instant file found for year {year}")
        ds_instant = xr.open_dataset(nc_file_instant)
        ds_point = ds_instant.sel(latitude=lat, longitude=lon, method='nearest')
        ds_month = ds_point.sel(valid_time=ds_point.valid_time.dt.month == month)
        if len(ds_month.valid_time) == 0:
            ds_month = ds_point
        results = {}
        results['t2m'] = float(ds_month['t2m'].mean().values) - 273.15
        t2m_k = float(ds_month['t2m'].mean().values)
        d2m_k = float(ds_month['d2m'].mean().values)
        results['humidity_pct'] = float(calculate_relative_humidity(t2m_k, d2m_k))
        results['u10'] = float(ds_month['u10'].mean().values)
        results['v10'] = float(ds_month['v10'].mean().values)
        results['wind_speed'] = np.sqrt(results['u10']**2 + results['v10']**2)
        results['sp_hpa'] = float(ds_month['sp'].mean().values) / 100.0
        results['blh'] = float(ds_month['blh'].mean().values)
        ds_instant.close()
        # Precipitation
        nc_file_accum = find_era5_file(year, 'accum')
        if nc_file_accum:
            ds_accum = xr.open_dataset(nc_file_accum)
            ds_point_accum = ds_accum.sel(latitude=lat, longitude=lon, method='nearest')
            ds_month_accum = ds_point_accum.sel(valid_time=ds_point_accum.valid_time.dt.month == month)
            results['tp_mm'] = float(ds_month_accum['tp'].sum().values) * 1000.0 if len(ds_month_accum.valid_time) > 0 else 0.0
            ds_accum.close()
        else:
            results['tp_mm'] = 0.0
        return results
    else:
        # Forecast for year > 2023
        print(f"Forecasting meteorology for {year} using trend from 2020-2023...")
        forecast = forecast_for_year(lat, lon, month, year)
        # Ensure all required keys exist
        required = ['t2m', 'humidity_pct', 'u10', 'v10', 'wind_speed', 'sp_hpa', 'blh', 'tp_mm']
        for k in required:
            if k not in forecast:
                forecast[k] = 0.0
        return forecast

# Test block
if __name__ == "__main__":
    print("Testing Delhi, January 2024 (forecast):")
    meteo = get_monthly_climatology(28.6139, 77.2090, month=1, year=2024)
    for k, v in meteo.items():
        print(f"  {k}: {v}")