import pandas as pd
import numpy as np
import argparse
import os

def calculate_top_contributions(target_grid_id, timestamp_str, footprint_file, aggregated_grid_file, events_file, output_dir):
    print(f"Calculating contributions for {target_grid_id} at {timestamp_str}")
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f'contributions_{target_grid_id}.csv')
    
    footprints = pd.read_csv(footprint_file)
    cpcb = pd.read_csv(aggregated_grid_file)
    events = pd.read_csv(events_file)
    
    fp_target = footprints[(footprints['target_grid_id'] == target_grid_id)].copy()
    if fp_target.empty:
        print(f"No footprint data found for {target_grid_id}")
        return None
        
    target_dt = pd.to_datetime(timestamp_str)
    
    # We expect aggregated grid file to correspond exactly to this timestamp, but to be robust:
    # Actually, aggregated grid file is generated specifically per timestamp in the new architecture.
    # So we just use it directly.
    cpcb_t = cpcb.copy()
    
    contrib = pd.merge(fp_target, cpcb_t[['grid_id', 'cell_AQI']], 
                       left_on='source_grid_id', right_on='grid_id', how='left')
    
    contrib = contrib.rename(columns={'cell_AQI': 'baseline_pollution_indicator'})
    contrib['baseline_pollution_indicator'] = contrib['baseline_pollution_indicator'].fillna(0.0)
    
    S_i = 1.0
    for _, evt in events.iterrows():
        if evt['date'] in timestamp_str:
            S_i = 1.5
            break
            
    # Equation: C_ij = W_ij * B_i * S_i
    contrib['estimated_pollution_contribution'] = contrib['footprint_normalized'] * contrib['baseline_pollution_indicator'] * S_i
    
    total_contrib = contrib['estimated_pollution_contribution'].sum()
    if total_contrib > 0:
        contrib['contribution_percent'] = 100 * contrib['estimated_pollution_contribution'] / total_contrib
    else:
        contrib['contribution_percent'] = 0.0
        
    # Rank all sources
    contrib = contrib.sort_values(by='estimated_pollution_contribution', ascending=False).reset_index(drop=True)
    contrib['rank'] = range(1, len(contrib) + 1)
    
    final_cols = ['rank', 'source_grid_id', 'distance_km', 'wind_speed', 'wind_direction', 
                  'footprint_weight', 'baseline_pollution_indicator', 'estimated_pollution_contribution', 'contribution_percent', 'pct_mass_outside_domain']
    
    # Take top 5 and aggregate the rest
    top5 = contrib.head(5).copy()
    if len(contrib) > 5:
        remaining = contrib.iloc[5:].copy()
        remaining_row = {
            'rank': 999,
            'source_grid_id': 'REMAINING_SOURCES',
            'distance_km': remaining['distance_km'].mean(),
            'wind_speed': remaining['wind_speed'].mean(),
            'wind_direction': remaining['wind_direction'].mean(),
            'footprint_weight': remaining['footprint_weight'].sum(),
            'baseline_pollution_indicator': remaining['baseline_pollution_indicator'].mean(),
            'estimated_pollution_contribution': remaining['estimated_pollution_contribution'].sum(),
            'contribution_percent': remaining['contribution_percent'].sum(),
            'pct_mass_outside_domain': remaining['pct_mass_outside_domain'].iloc[0] if 'pct_mass_outside_domain' in remaining.columns else 0.0
        }
        top5 = pd.concat([top5, pd.DataFrame([remaining_row])], ignore_index=True)
    
    top5 = top5[final_cols]
    top5.to_csv(out_file, index=False)
    print(f"Saved contributions to {out_file}")
    
    return out_file

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', type=str, required=True)
    parser.add_argument('--time', type=str, required=True)
    parser.add_argument('--footprint', type=str, required=True)
    parser.add_argument('--cpcb_aggregated', type=str, required=True)
    parser.add_argument('--events', type=str, default='data/raw/events/india_festivals.csv')
    parser.add_argument('--out_dir', type=str, default='data/processed/contributions')
    args = parser.parse_args()
    
    calculate_top_contributions(args.target, args.time, args.footprint, args.cpcb_aggregated, args.events, args.out_dir)
