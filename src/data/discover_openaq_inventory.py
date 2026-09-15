"""
OPENAQ DATA INVENTORY & DISCOVERY SCRIPT (PHASE A)
==================================================
Discovers all Indian PM2.5 monitoring locations available in OpenAQ.
Scans station metadata, queries public OpenAQ archive for historical coverage,
and compiles a comprehensive discovery inventory.

Outputs:
- data/real/openaq/station_inventory_discovery.csv
- data/real/openaq/city_discovery_summary.csv
"""

import os
import concurrent.futures
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

S3_BASE_URL = "https://openaq-data-archive.s3.amazonaws.com"
XML_NS = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}


def check_location_availability(loc_row):
    """
    Checks S3 archive for a single location ID:
    Finds available years, approximate file count, and date ranges.
    """
    loc_id = loc_row['id']
    loc_name = loc_row.get('name', 'Unknown')
    lat = loc_row.get('coordinates.latitude', np.nan)
    lon = loc_row.get('coordinates.longitude', np.nan)

    # Prefix for this location
    prefix = f"records/csv.gz/locationid={loc_id}/"
    url = f"{S3_BASE_URL}/"

    try:
        r = requests.get(url, params={'list-type': 2, 'prefix': prefix, 'delimiter': '/', 'max-keys': 50}, timeout=10)
        if r.status_code != 200:
            return None

        root = ET.fromstring(r.text)
        prefixes = [p.find('s3:Prefix', XML_NS).text for p in root.findall('s3:CommonPrefixes', XML_NS)]
        years = [p.split('year=')[-1].rstrip('/') for p in prefixes if 'year=' in p]

        if not years:
            return None

        # Check total file count across available years (up to 1000 keys)
        r_files = requests.get(url, params={'list-type': 2, 'prefix': prefix, 'max-keys': 1000}, timeout=15)
        root_files = ET.fromstring(r_files.text)
        keys = [k.find('s3:Key', XML_NS).text for k in root_files.findall('s3:Contents', XML_NS)]

        if not keys:
            return None

        # Sort keys to find earliest and latest date
        sorted_keys = sorted(keys)
        first_key = sorted_keys[0]
        last_key = sorted_keys[-1]

        # Extract dates from filenames (e.g., location-235-20150629.csv.gz)
        def extract_date(k):
            fname = k.split('/')[-1]
            parts = fname.replace('.csv.gz', '').split('-')
            if len(parts) >= 3:
                dstr = parts[-1]
                if len(dstr) == 8 and dstr.isdigit():
                    return f"{dstr[:4]}-{dstr[4:6]}-{dstr[6:]}"
            return "Unknown"

        earliest_date = extract_date(first_key)
        latest_date = extract_date(last_key)

        return {
            "station_id": loc_id,
            "station_name": loc_name,
            "latitude": lat,
            "longitude": lon,
            "years_available": ",".join(sorted(years)),
            "file_count": len(keys),
            "earliest_date": earliest_date,
            "latest_date": latest_date,
            "s3_prefix": prefix
        }

    except Exception:
        return None


def run_discovery(output_dir="data/real/openaq"):
    os.makedirs(output_dir, exist_ok=True)
    metadata_file = "data/interim/openaq_in_locations.csv"

    if not os.path.exists(metadata_file):
        print(f"Error: {metadata_file} not found.")
        return

    print(f"Loading Indian OpenAQ station metadata from {metadata_file}...")
    df_loc = pd.read_csv(metadata_file)
    print(f"Found {len(df_loc)} total candidate Indian stations in metadata.")

    print("\n[Phase A — Discovery] Querying OpenAQ S3 data archive for historical data availability...")
    results = []

    # Query with concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        future_to_loc = {executor.submit(check_location_availability, row): row for _, row in df_loc.iterrows()}
        completed = 0
        total = len(df_loc)
        for future in concurrent.futures.as_completed(future_to_loc):
            completed += 1
            res = future.result()
            if res is not None:
                results.append(res)
            if completed % 100 == 0 or completed == total:
                print(f"Scanned {completed}/{total} stations... Found {len(results)} with active historical data.")

    df_inventory = pd.DataFrame(results)
    if df_inventory.empty:
        print("No active historical stations found.")
        return

    # Infer City / State from Station Name
    def infer_city(name):
        name_lower = str(name).lower()
        known_cities = [
            "delhi", "mumbai", "kolkata", "chennai", "bengaluru", "bangalore",
            "hyderabad", "ahmedabad", "pune", "jaipur", "lucknow", "kanpur",
            "varanasi", "patna", "bhopal", "indore", "nagpur", "surat",
            "vadodara", "chandigarh", "ludhiana", "amritsar", "agra",
            "ghaziabad", "noida", "gurugram", "gurgaon", "faridabad",
            "gaya", "muzaffarpur", "jodhpur", "kota", "udaipur", "visakhapatnam",
            "vijayawada", "guwahati", "dehradun", "ranchi", "jamshedpur",
            "thiruvananthapuram", "kochi", "coimbatore", "mysuru"
        ]
        for c in known_cities:
            if c in name_lower:
                if c == "bangalore": return "Bengaluru"
                if c == "gurgaon": return "Gurugram"
                return c.capitalize()
        # Fallback split
        if "-" in str(name):
            parts = str(name).split("-")
            for p in parts:
                p_clean = p.strip()
                if len(p_clean) > 3 and not any(char.isdigit() for char in p_clean):
                    return p_clean.split(",")[0].strip()
        return "Other_India"

    df_inventory["city"] = df_inventory["station_name"].apply(infer_city)
    df_inventory = df_inventory.sort_values(by="file_count", ascending=False).reset_index(drop=True)

    inv_path = os.path.join(output_dir, "station_inventory_discovery.csv")
    df_inventory.to_csv(inv_path, index=False)
    print(f"\n[Phase A — Discovery] Saved station inventory to: {inv_path} ({len(df_inventory)} active stations)")

    # City Summary
    city_summary = df_inventory.groupby("city").agg(
        number_of_stations=("station_id", "count"),
        total_archive_files=("file_count", "sum"),
        earliest_date=("earliest_date", "min"),
        latest_date=("latest_date", "max"),
        years_spanned=("years_available", lambda x: ",".join(sorted(set(",".join(x).split(",")))))
    ).reset_index().sort_values(by="total_archive_files", ascending=False)

    city_path = os.path.join(output_dir, "city_discovery_summary.csv")
    city_summary.to_csv(city_path, index=False)
    print(f"[Phase A — Discovery] Saved city discovery summary to: {city_path} ({len(city_summary)} cities)")

    print("\nTop 15 Cities by OpenAQ Historical Availability:")
    print(city_summary.head(15).to_string(index=False))


if __name__ == "__main__":
    run_discovery()
