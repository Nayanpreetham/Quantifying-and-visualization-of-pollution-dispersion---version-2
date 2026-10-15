import glob, os, pandas as pd

def check_all():
    print('=== Checking Monthly Transport Matrices ===')
    monthly_files = sorted(glob.glob('results/phase19_transport/monthly/*.parquet'))
    print(f'Total monthly files: {len(monthly_files)}')
    if monthly_files:
        sample_m = pd.read_parquet(monthly_files[0])
        print(f'Sample {monthly_files[0]}: shape={sample_m.shape}, cols={sample_m.columns.tolist()}')
        print(f'Sources count: {sample_m["source_grid_id"].nunique()}, Dests count: {sample_m["dest_grid_id"].nunique()}')
        print(f'Horizons: {sample_m["elapsed_time_hours"].unique().tolist()}')

    print('\n=== Checking Annual Transport Matrices ===')
    annual_files = sorted(glob.glob('results/phase19_transport/annual/*.parquet'))
    print(f'Total annual files: {len(annual_files)}')
    if annual_files:
        sample_a = pd.read_parquet(annual_files[0])
        print(f'Sample {annual_files[0]}: shape={sample_a.shape}, cols={sample_a.columns.tolist()}')

    print('\n=== Checking Pilot 2021 Transport Matrix ===')
    pilot_path = 'results/phase19_transport/pilot/transport_matrix_pilot_50km.csv'
    if os.path.exists(pilot_path):
        df_p = pd.read_csv(pilot_path, nrows=5)
        print(f'Pilot sample cols: {df_p.columns.tolist()}')
        df_p_full = pd.read_csv(pilot_path)
        print(f'Pilot full shape: {df_p_full.shape}')
        print(f'Pilot sources: {df_p_full["source_grid_id"].nunique()}, dests: {df_p_full["dest_grid_id"].nunique()}')

    print('\n=== Checking Pilot Corrected ===')
    cor_path = 'results/phase19_transport/correction_audit/pilot/transport_matrix_pilot_corrected_50km.csv'
    if os.path.exists(cor_path):
        df_c = pd.read_csv(cor_path)
        print(f'Pilot corrected shape: {df_c.shape}')
        print(f'Pilot corrected sources: {df_c["source_grid_id"].nunique()}, dests: {df_c["dest_grid_id"].nunique()}')
        print(f'Pilot corrected horizons: {df_c["elapsed_time_hours"].unique().tolist()}')

if __name__ == '__main__':
    check_all()
