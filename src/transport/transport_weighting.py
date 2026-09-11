import pandas as pd
import os

def calculate_transport_weighted_contribution(target_grid_id, timestamp_str, transport_influence_file, aggregated_grid_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f'contributions_{target_grid_id}.csv')
    
    transport = pd.read_csv(transport_influence_file)
    cpcb = pd.read_csv(aggregated_grid_file)
    
    if transport.empty:
        return None
        
    contrib = pd.merge(transport, cpcb[['grid_id', 'cell_AQI']], 
                       left_on='source_grid_id', right_on='grid_id', how='left')
                       
    contrib = contrib.rename(columns={'cell_AQI': 'baseline_pollution_indicator'})
    contrib['baseline_pollution_indicator'] = contrib['baseline_pollution_indicator'].fillna(0.0)
    
    S_i = 1.0 # Seasonal modifier placeholder
    
    # C_ij = T_ij * B_i * S_i
    contrib['estimated_pollution_contribution'] = contrib['transport_weight'] * contrib['baseline_pollution_indicator'] * S_i
    
    total_contrib = contrib['estimated_pollution_contribution'].sum()
    if total_contrib > 0:
        contrib['contribution_percent'] = 100 * contrib['estimated_pollution_contribution'] / total_contrib
    else:
        contrib['contribution_percent'] = 0.0
        
    contrib = contrib.sort_values(by='estimated_pollution_contribution', ascending=False).reset_index(drop=True)
    contrib['rank'] = range(1, len(contrib) + 1)
    
    final_cols = ['rank', 'source_grid_id', 'distance_km', 'transport_weight', 
                  'baseline_pollution_indicator', 'estimated_pollution_contribution', 
                  'contribution_percent', 'pct_mass_outside_domain']
                  
    # Top 5
    top5 = contrib.head(5).copy()
    if len(contrib) > 5:
        remaining = contrib.iloc[5:].copy()
        remaining_row = {
            'rank': 999,
            'source_grid_id': 'REMAINING_SOURCES',
            'distance_km': remaining['distance_km'].mean(),
            'transport_weight': remaining['transport_weight'].sum(),
            'baseline_pollution_indicator': remaining['baseline_pollution_indicator'].mean(),
            'estimated_pollution_contribution': remaining['estimated_pollution_contribution'].sum(),
            'contribution_percent': remaining['contribution_percent'].sum(),
            'pct_mass_outside_domain': remaining['pct_mass_outside_domain'].iloc[0] if 'pct_mass_outside_domain' in remaining.columns else 0.0
        }
        top5 = pd.concat([top5, pd.DataFrame([remaining_row])], ignore_index=True)
        
    top5 = top5[final_cols]
    top5.to_csv(out_file, index=False)
    
    return out_file
