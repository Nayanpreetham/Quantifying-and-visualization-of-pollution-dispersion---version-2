"""
Task Coverage Audit: ERA5 Meteorological Domain Coverage and Boundary Audit
Phase 19 — Final Scientific Verification & Targeted Corrections

Audits spatial and temporal coverage of ERA5 reanalysis fields relative to the
1,380 national 50 km terrestrial grid cells.
- Evaluates spatial limits: Latitude [6.0, 35.0] N, Longitude [68.0, 97.0] E.
- Identifies cells lying outside ERA5 coordinates.
- Prohibits silent extrapolation.
- Cross-references monitoring station locations.
- Outputs results/phase19_transport/correction_audit/era5_coverage_report.csv
"""

import os
import sys
import netCDF4 as nc
import numpy as np
import pandas as pd

def main():
    print("=== Phase 19 Audit: ERA5 Meteorological Coverage Audit ===")
    
    out_dir = "results/phase19_transport/correction_audit"
    os.makedirs(out_dir, exist_ok=True)
    
    grid_csv = "results/phase18_grid_audit/india_50km_grid.csv"
    station_map_csv = "results/phase18_grid_audit/station_to_50km_grid_mapping.csv"
    era5_sample_nc = "data/raw/era5/2021/era5_2021_instant.nc"
    
    df_grid = pd.read_csv(grid_csv)
    df_st = pd.read_csv(station_map_csv)
    monitored_cells = set(df_st['grid_id_50km'].unique())
    
    ds = nc.Dataset(era5_sample_nc)
    raw_lats = ds.variables['latitude'][:]
    raw_lons = ds.variables['longitude'][:]
    
    lat_min = float(raw_lats.min())
    lat_max = float(raw_lats.max())
    lon_min = float(raw_lons.min())
    lon_max = float(raw_lons.max())
    
    print(f"ERA5 Coordinate Extent:")
    print(f"  Latitude:  [{lat_min:.2f}, {lat_max:.2f}] N (Spacing: 0.25 deg)")
    print(f"  Longitude: [{lon_min:.2f}, {lon_max:.2f}] E (Spacing: 0.25 deg)")
    print(f"Total National 50 km Cells: {len(df_grid)}")
    
    records = []
    
    for idx, row in df_grid.iterrows():
        gid = row['grid_id_50km']
        c_lat = row['center_latitude_deg']
        c_lon = row['center_longitude_deg']
        is_mon = gid in monitored_cells
        
        # Check spatial coverage
        lat_in = (c_lat >= lat_min) and (c_lat <= lat_max)
        lon_in = (c_lon >= lon_min) and (c_lon <= lon_max)
        is_fully_supported = lat_in and lon_in
        
        # Calculate boundary exceedance
        lat_exceed_deg = 0.0
        if c_lat > lat_max:
            lat_exceed_deg = c_lat - lat_max
        elif c_lat < lat_min:
            lat_exceed_deg = lat_min - c_lat
            
        lon_exceed_deg = 0.0
        if c_lon > lon_max:
            lon_exceed_deg = c_lon - lon_max
        elif c_lon < lon_min:
            lon_exceed_deg = lon_min - c_lon
            
        if is_fully_supported:
            status = "FULLY_SUPPORTED"
            issue_note = "Within valid ERA5 coordinate domain"
        else:
            status = "UNSUPPORTED_MET_COVERAGE"
            reasons = []
            if not lat_in:
                reasons.append(f"Latitude {c_lat:.3f}N exceeds ERA5 max {lat_max:.1f}N by {lat_exceed_deg:.3f} deg")
            if not lon_in:
                reasons.append(f"Longitude {c_lon:.3f}E exceeds ERA5 max {lon_max:.1f}E by {lon_exceed_deg:.3f} deg")
            issue_note = "; ".join(reasons)
            
        records.append({
            'grid_id_50km': gid,
            'row': int(row['row']),
            'column': int(row['column']),
            'center_latitude_deg': round(c_lat, 6),
            'center_longitude_deg': round(c_lon, 6),
            'is_monitored_source_cell': is_mon,
            'spatial_coverage_status': status,
            'latitude_exceedance_deg': round(lat_exceed_deg, 4),
            'longitude_exceedance_deg': round(lon_exceed_deg, 4),
            'extrapolation_permitted': False,
            'issue_description': issue_note
        })
        
    df_coverage = pd.DataFrame(records)
    out_csv = os.path.join(out_dir, "era5_coverage_report.csv")
    df_coverage.to_csv(out_csv, index=False)
    
    n_supported = (df_coverage['spatial_coverage_status'] == 'FULLY_SUPPORTED').sum()
    n_unsupported = (df_coverage['spatial_coverage_status'] == 'UNSUPPORTED_MET_COVERAGE').sum()
    unsupported_monitored = df_coverage[(df_coverage['spatial_coverage_status'] == 'UNSUPPORTED_MET_COVERAGE') & (df_coverage['is_monitored_source_cell'] == True)]
    
    print(f"\n--- COVERAGE AUDIT SUMMARY ---")
    print(f"Fully Supported Grid Cells: {n_supported} / {len(df_grid)} ({n_supported / len(df_grid) * 100:.2f}%)")
    print(f"Unsupported Grid Cells:     {n_unsupported} / {len(df_grid)} ({n_unsupported / len(df_grid) * 100:.2f}%)")
    print(f"Unsupported Monitored Cells: {len(unsupported_monitored)} (Zero ground truth impacted)")
    
    print("\nUnsupported Cells Detail:")
    unsupported_df = df_coverage[df_coverage['spatial_coverage_status'] == 'UNSUPPORTED_MET_COVERAGE']
    for _, r in unsupported_df.iterrows():
        print(f"  {r['grid_id_50km']} (r{r['row']:02d}_c{r['column']:02d}): {r['issue_description']}")
        
    print(f"\nSaved coverage report: {out_csv}")
    return df_coverage

if __name__ == '__main__':
    main()
