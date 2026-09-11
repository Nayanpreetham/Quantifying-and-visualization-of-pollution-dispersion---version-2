import requests
import pandas as pd
import os
import concurrent.futures
from datetime import datetime
import time

API_KEY = "985bdc07c5e4d052e54ed0b2a110d646b5ba507d1c749a3d71aaf6fede3cceeb"
HEADERS = {"X-API-Key": API_KEY}

def get_india_pm25_sensors():
    print("Fetching all India locations from OpenAQ v3 API...")
    url = "https://api.openaq.org/v3/locations"
    sensors_info = []
    
    page = 1
    while True:
        resp = requests.get(url, headers=HEADERS, params={'iso': 'IN', 'limit': 100, 'page': page})
        if resp.status_code == 429:
            print("Rate limited on locations. Sleeping 5s...")
            time.sleep(5)
            continue
        elif resp.status_code != 200:
            print(f"Error fetching locations: {resp.status_code}")
            break
            
        data = resp.json()
        results = data.get('results', [])
        if not results:
            break
            
        for loc in results:
            coords = loc.get('coordinates', {})
            lat = coords.get('latitude')
            lon = coords.get('longitude')
            if lat is None or lon is None:
                continue
                
            for sensor in loc.get('sensors', []):
                param = sensor.get('parameter', {})
                if param.get('name') == 'pm25':
                    sensors_info.append({
                        'sensor_id': sensor['id'],
                        'lat': lat,
                        'lon': lon
                    })
                    
        print(f"Page {page}: found {len(sensors_info)} PM2.5 sensors so far...")
        if len(results) < 100:
            break
        page += 1
        time.sleep(0.5) # Prevent 429
        
    return sensors_info

def fetch_sensor_data(sensor_info, date_str):
    sensor_id = sensor_info['sensor_id']
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours"
    params = {
        'datetime_from': f"{date_str}T00:00:00Z",
        'datetime_to': f"{date_str}T23:59:59Z",
        'limit': 24
    }
    
    for _ in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            if resp.status_code == 429:
                time.sleep(2)
                continue
            if resp.status_code == 200:
                results = resp.json().get('results', [])
                if results:
                    # Calculate daily mean
                    values = [r['value'] for r in results if r.get('value') is not None and r.get('value') >= 0]
                    if values:
                        mean_val = sum(values) / len(values)
                        return {
                            'lat': sensor_info['lat'],
                            'lon': sensor_info['lon'],
                            'pm25': mean_val
                        }
                return None
        except Exception:
            time.sleep(1)
            
    return None

def fetch_openaq_spatial(date_str="2020-11-01"):
    sensors = get_india_pm25_sensors()
    print(f"\nTotal PM2.5 sensors found in India: {len(sensors)}")
    
    # We only care about coordinates within bounding box: 5 to 38 N, 68 to 98 E
    filtered_sensors = [
        s for s in sensors 
        if 5.0 <= s['lat'] <= 38.0 and 68.0 <= s['lon'] <= 98.0
    ]
    # For speed of the script to prove kriging works, we can limit to first 100 sensors if there are thousands
    if len(filtered_sensors) > 200:
        print(f"Found {len(filtered_sensors)} sensors. Limiting to 200 for safe API usage...")
        filtered_sensors = filtered_sensors[:200]
    else:
        print(f"Sensors within bounding box: {len(filtered_sensors)}")
    
    print(f"Fetching measurements for {date_str} using ThreadPoolExecutor (max_workers=3)...")
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_sensor_data, s, date_str): s for s in filtered_sensors}
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            res = future.result()
            if res:
                results.append(res)
            if i % 100 == 0:
                print(f"Processed {i}/{len(filtered_sensors)} sensors...")
                
    if not results:
        print("No data found for this date.")
        return
        
    df = pd.DataFrame(results)
    
    # Average overlapping coordinates
    spatial_df = df.groupby(['lat', 'lon'], as_index=False)['pm25'].mean()
    
    os.makedirs('data/raw/openaq', exist_ok=True)
    out_path = f'data/raw/openaq/spatial_pm25_{date_str}.csv'
    spatial_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(spatial_df)} unique coordinate points to {out_path}")

if __name__ == "__main__":
    # Let's fetch a more recent date if 2020-11-01 is empty due to API retention,
    # but OpenAQ usually stores all history.
    fetch_openaq_spatial("2020-11-01")
