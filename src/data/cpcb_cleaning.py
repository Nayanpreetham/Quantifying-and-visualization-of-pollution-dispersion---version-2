import pandas as pd
import numpy as np
import argparse
import os

def clean_cpcb_data(input_file, output_dir, freq='1h', max_gap_hours=3):
    print(f"Cleaning observations from {input_file}...")
    df = pd.read_csv(input_file)
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, 'cpcb_cleaned.csv')
    
    df['datetime'] = pd.to_datetime(df['datetime'])
    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize('UTC')
        
    # Drop completely duplicate rows
    df = df.drop_duplicates()
    
    # Identify stations and parameters
    stations = df[['locationId', 'latitude', 'longitude']].drop_duplicates(subset=['locationId']).set_index('locationId')
    
    # Track provenance manually if missing
    provenance_cols = ['source_provider', 'source_dataset', 'original_station_id', 'source_url', 'download_timestamp', 'unit']
    for col in provenance_cols:
        if col not in df.columns:
            df[col] = 'UNKNOWN'
    prov_data = df.groupby('locationId')[provenance_cols].first()
    
    # 2. Impossible coordinates
    invalid_coords = (df['latitude'] < 6.0) | (df['latitude'] > 38.0) | (df['longitude'] < 68.0) | (df['longitude'] > 98.0)
    df.loc[invalid_coords, ['latitude', 'longitude']] = np.nan
    
    # 3. Impossible negative concentrations
    if 'value' in df.columns:
        df.loc[df['value'] < 0, 'value'] = np.nan
        
    df = df.drop_duplicates(subset=['locationId', 'parameter', 'datetime'], keep='first')
    
    # Resample to strict regular frequency per location & parameter
    clean_dfs = []
    
    # Group by location and parameter
    grouped = df.groupby(['locationId', 'parameter'])
    for (loc, param), group in grouped:
        group = group.sort_values('datetime').set_index('datetime')
        if group.empty: continue
        
        # Determine temporal bounds for this station
        start_time = group.index.min().floor('h')
        end_time = group.index.max().ceil('h')
        
        if start_time == end_time:
            # Only one data point
            full_idx = [start_time]
        else:
            full_idx = pd.date_range(start=start_time, end=end_time, freq=freq)
        
        # Reindex to force explicit NaNs for missing timestamps
        resampled = group.reindex(full_idx)
        resampled['locationId'] = loc
        resampled['parameter'] = param
        
        # Restore static station info
        resampled['latitude'] = stations.loc[loc, 'latitude']
        resampled['longitude'] = stations.loc[loc, 'longitude']
        
        for col in provenance_cols:
            resampled[col] = prov_data.loc[loc, col]
            
        resampled['is_observed'] = ~resampled['value'].isna()
        resampled['is_imputed'] = False
        resampled['imputation_method'] = 'none'
        resampled['quality_flag'] = np.where(resampled['is_observed'], 'valid', 'missing')
        
        # Impute short gaps
        # Interpolate time (linear), limited to max_gap_hours
        interpolated = resampled['value'].interpolate(method='time', limit=max_gap_hours)
        
        # Find which values were newly filled
        imputed_mask = resampled['value'].isna() & interpolated.notna()
        
        resampled['value'] = interpolated
        resampled.loc[imputed_mask, 'is_imputed'] = True
        resampled.loc[imputed_mask, 'imputation_method'] = 'linear_interpolation'
        resampled.loc[imputed_mask, 'quality_flag'] = 'imputed'
        
        resampled = resampled.reset_index().rename(columns={'index': 'datetime'})
        clean_dfs.append(resampled)

    if clean_dfs:
        final_df = pd.concat(clean_dfs, ignore_index=True)
    else:
        final_df = df # Fallback if totally empty

    # Filter out stations without coordinates
    final_df = final_df.dropna(subset=['latitude', 'longitude'])
    
    final_df.to_csv(out_file, index=False)
    print(f"Saved cleaned data with {final_df['is_imputed'].sum()} imputed rows to {out_file}")
    return out_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True)
    parser.add_argument('--out_dir', type=str, default='data/interim/cpcb')
    args = parser.parse_args()
    clean_cpcb_data(args.input, args.out_dir)
