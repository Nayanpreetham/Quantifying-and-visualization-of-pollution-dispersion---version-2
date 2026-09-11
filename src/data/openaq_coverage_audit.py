import requests
import pandas as pd
import time
import os

API_KEY = os.environ.get('OPENAQ_API_KEY', '985bdc07c5e4d052e54ed0b2a110d646b5ba507d1c749a3d71aaf6fede3cceeb')
HEADERS = {'X-API-Key': API_KEY}
BASE_URL = 'https://api.openaq.org/v3'

def run_audit():
    print("Fetching OpenAQ locations for India (IN) using v3 API...")
    india_id = 9
    
    locations = []
    page = 1
    limit = 100
    
    while True:
        url = f"{BASE_URL}/locations?countries_id={india_id}&limit={limit}&page={page}"
        print(f"Fetching page {page}...")
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"Error fetching locations: {resp.text}")
            break
        data = resp.json().get('results', [])
        if not data:
            break
        locations.extend(data)
        page += 1
        time.sleep(1) # respectful delay to avoid rate limits
        
    if not locations:
        print("No locations found.")
        return
        
    df = pd.json_normalize(locations)
    os.makedirs("data/interim", exist_ok=True)
    df.to_csv("data/interim/openaq_in_locations.csv", index=False)
    
    print("\n" + "="*50)
    print("OPENAQ COVERAGE AUDIT FOR INDIA")
    print("="*50)
    
    total_stations = len(df)
    print(f"\nTotal OpenAQ Stations in India: {total_stations}")
    print("Official CPCB Station Count (approx): ~450-500")
    
    # Analyze Providers
    if 'provider.name' in df.columns:
        cpcb_stations = df[df['provider.name'].str.contains('CPCB|Central Pollution', na=False, case=False)]
        print(f"Stations explicitly provided by CPCB in OpenAQ: {len(cpcb_stations)}")
        print(f"Stations missing from OpenAQ (vs ~500 official): ~{max(0, 500 - len(cpcb_stations))}")
    else:
        print("Provider information not detailed in v3 response. Need to check manufacturers or names.")
        
    print("\nTop 10 Cities/Regions by Station Count:")
    if 'locality' in df.columns:
        print(df['locality'].value_counts().head(10))
    elif 'city' in df.columns:
        print(df['city'].value_counts().head(10))
        
    print("\nTemporal Coverage:")
    if 'datetimeFirst' in df.columns and 'datetimeLast' in df.columns:
        df['datetimeFirst'] = pd.to_datetime(df['datetimeFirst'], errors='coerce')
        df['datetimeLast'] = pd.to_datetime(df['datetimeLast'], errors='coerce')
        active_2020 = len(df[df['datetimeFirst'].dt.year <= 2020])
        print(f"Stations active since 2020 or earlier: {active_2020}")
        
    print("\nAudit complete. Data saved to data/interim/openaq_in_locations.csv")
    
if __name__ == '__main__':
    run_audit()
