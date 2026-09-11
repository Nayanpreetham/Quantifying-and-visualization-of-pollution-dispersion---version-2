import requests
import pandas as pd
import os

API_KEY = "985bdc07c5e4d052e54ed0b2a110d646b5ba507d1c749a3d71aaf6fede3cceeb"
HEADERS = {"X-API-Key": API_KEY}

def fetch_openaq(date_str="2020-11-01"):
    print(f"Fetching OpenAQ PM2.5 data for India on {date_str}...")
    url = "https://api.openaq.org/v2/measurements"
    
    # We will fetch for the whole day, then average per coordinate
    params = {
        "country": "IN",
        "parameter": "pm25",
        "date_from": f"{date_str}T00:00:00Z",
        "date_to": f"{date_str}T23:59:59Z",
        "limit": 10000,
        "page": 1
    }
    
    all_results = []
    while True:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"Error {resp.status_code}: {resp.text}")
            break
            
        data = resp.json()
        results = data.get("results", [])
        if not results:
            break
            
        all_results.extend(results)
        print(f"Fetched page {params['page']} ({len(results)} records)...")
        
        # Check if we need to paginate
        meta = data.get("meta", {})
        found = meta.get("found", 0)
        
        # OpenAQ v2 limits to 100,000 records sometimes or pages. If we have it all, break
        if len(all_results) >= found:
            break
            
        params["page"] += 1
        
    if not all_results:
        print("No data found.")
        return
        
    # Process into dataframe
    records = []
    for r in all_results:
        coords = r.get('coordinates', {})
        if coords and 'latitude' in coords and 'longitude' in coords:
            records.append({
                'lat': coords['latitude'],
                'lon': coords['longitude'],
                'pm25': r.get('value')
            })
            
    df = pd.DataFrame(records)
    df = df.dropna()
    
    # Filter negative outliers
    df = df[df['pm25'] >= 0]
    
    # Average over the day per coordinate to get the spatial field
    spatial_df = df.groupby(['lat', 'lon'], as_index=False)['pm25'].mean()
    
    # Bounding box filter (5 to 38 N, 68 to 98 E) just to be safe
    spatial_df = spatial_df[
        (spatial_df['lat'] >= 5.0) & (spatial_df['lat'] <= 38.0) &
        (spatial_df['lon'] >= 68.0) & (spatial_df['lon'] <= 98.0)
    ]
    
    os.makedirs('data/raw/openaq', exist_ok=True)
    out_path = f'data/raw/openaq/spatial_pm25_{date_str}.csv'
    spatial_df.to_csv(out_path, index=False)
    print(f"\nSaved {len(spatial_df)} unique coordinate points to {out_path}")

if __name__ == "__main__":
    fetch_openaq("2020-11-01")
