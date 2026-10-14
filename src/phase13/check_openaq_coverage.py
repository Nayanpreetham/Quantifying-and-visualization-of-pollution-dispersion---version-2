import pandas as pd

df_obs = pd.read_csv('data/real/openaq/pm25_observations.csv')
print(f'Total rows: {len(df_obs):,}')
df_obs['dt'] = pd.to_datetime(df_obs['timestamp_utc']).dt.tz_localize(None)
print(f"Min timestamp: {df_obs['dt'].min()}")
print(f"Max timestamp: {df_obs['dt'].max()}")
df_obs['year'] = df_obs['dt'].dt.year
print('\nYearly breakdown:')
print(df_obs.groupby('year').agg(
    obs_count=('pm25', 'count'),
    station_count=('station_id', 'nunique'),
    min_date=('dt', 'min'),
    max_date=('dt', 'max')
))
