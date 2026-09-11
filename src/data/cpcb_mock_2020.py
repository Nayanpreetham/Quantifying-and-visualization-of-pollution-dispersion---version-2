import pandas as pd
import os

print("Generating MOCK PM2.5 measurements for 2020-11-01 12:00:00 UTC...")
locations_df = pd.read_csv('data/interim/openaq_in_locations.csv')
cpcb_locs = locations_df[locations_df['provider.name'].str.contains('CPCB', na=False, case=False)].copy()

# Sample 150 stations
stations = cpcb_locs.sample(min(150, len(cpcb_locs)), random_state=42)

measurements = []
for _, row in stations.iterrows():
    # Make up a realistic PM2.5 value based on latitude (North India higher)
    lat = row['coordinates.latitude']
    val = max(10, (lat - 10) * 10 + 50) # Very rough dummy
    measurements.append({
        'locationId': row['id'],
        'parameter': 'pm25',
        'value': val,
        'datetime': '2020-11-01T12:00:00Z',
        'latitude': lat,
        'longitude': row['coordinates.longitude'],
        'source_provider': 'CPCB_MOCK',
        'source_dataset': 'Pilot_MOCK',
        'original_station_id': row['name']
    })
    
df = pd.DataFrame(measurements)
os.makedirs('data/raw/cpcb', exist_ok=True)
df.to_csv('data/raw/cpcb/openaq_2020_11_01.csv', index=False)
print(f"Saved {len(df)} MOCK measurements assigned to 2020-11-01 12:00:00Z.")
