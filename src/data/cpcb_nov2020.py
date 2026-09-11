import requests
import pandas as pd
import os
import sys
import ast

API_KEY = os.environ.get('OPENAQ_API_KEY', '985bdc07c5e4d052e54ed0b2a110d646b5ba507d1c749a3d71aaf6fede3cceeb')
HEADERS = {'X-API-Key': API_KEY}
BASE_URL = 'https://api.openaq.org/v3'

def fetch_real_measurements():
    print("Fetching REAL OpenAQ PM2.5 measurements for 2020-11-01...")
    
    locations_df = pd.read_csv('data/interim/openaq_in_locations.csv')
    cpcb_locs = locations_df[locations_df['provider.name'].str.contains('CPCB', na=False, case=False)].copy()
    
    def get_pm25_sensor_id(sensors_str):
        try:
            sensors = ast.literal_eval(sensors_str)
            for s in sensors:
                if s.get('parameter', {}).get('name') == 'pm25':
                    return s.get('id')
        except:
            return None
        return None
        
    cpcb_locs['pm25_sensor_id'] = cpcb_locs['sensors'].apply(get_pm25_sensor_id)
    cpcb_locs = cpcb_locs.dropna(subset=['pm25_sensor_id'])
    
    measurements = []
    
    # We want active stations in Nov 2020
    # First dt <= 2020-11-01 and Last dt >= 2020-11-01
    cpcb_locs['first_dt'] = pd.to_datetime(cpcb_locs['datetimeFirst.utc'], errors='coerce')
    cpcb_locs['last_dt'] = pd.to_datetime(cpcb_locs['datetimeLast.utc'], errors='coerce')
    
    target_date = pd.to_datetime('2020-11-01T00:00:00Z')
    valid_locs = cpcb_locs[(cpcb_locs['first_dt'] <= target_date) & (cpcb_locs['last_dt'] >= target_date)]
    
    target_cities = ['Delhi', 'Lucknow', 'Varanasi', 'Kanpur', 'Patna', 'Kolkata', 'Mumbai', 'Ahmedabad', 'Hyderabad', 'Bengaluru']
    
    sensor_ids = []
    location_data = {}
    
    for city in target_cities:
        city_stations = valid_locs[valid_locs['name'].str.contains(city, na=False, case=False)]
        if not city_stations.empty:
            for _, row in city_stations.head(5).iterrows():
                sid = row['pm25_sensor_id']
                sensor_ids.append(sid)
                location_data[sid] = row
            
    # Add random ones to reach ~100
    remaining = valid_locs[~valid_locs['pm25_sensor_id'].isin(sensor_ids)]
    for _, row in remaining.head(100 - len(sensor_ids)).iterrows():
        sid = row['pm25_sensor_id']
        sensor_ids.append(sid)
        location_data[sid] = row
            
    print(f"Querying {len(sensor_ids)} sensors for historical data...")
    
    for sid in sensor_ids:
        sys.stdout.write(f"Querying sensor {sid}... ")
        sys.stdout.flush()
        url = f"{BASE_URL}/sensors/{int(sid)}/measurements?date_from=2020-11-01T12:00:00Z&date_to=2020-11-01T13:00:00Z&limit=1"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    r = results[0]
                    row = location_data[sid]
                    measurements.append({
                        'locationId': row['id'],
                        'parameter': 'pm25',
                        'value': r.get('value'),
                        'datetime': r.get('period', {}).get('datetimeFrom', {}).get('utc'),
                        'latitude': row['coordinates.latitude'],
                        'longitude': row['coordinates.longitude']
                    })
                    print(f"Found {r.get('value')} µg/m³")
                else:
                    print("No data in this window.")
            else:
                print(f"Error {resp.status_code}")
        except Exception as e:
            print(f"Failed: {e}")
            
    df = pd.DataFrame(measurements)
    if not df.empty:
        os.makedirs('data/raw/cpcb', exist_ok=True)
        df.to_csv('data/raw/cpcb/openaq_2020_11_01.csv', index=False)
        print(f"Saved {len(df)} REAL measurements.")
    else:
        print("No real measurements found for this period in queried stations.")

if __name__ == '__main__':
    fetch_real_measurements()
