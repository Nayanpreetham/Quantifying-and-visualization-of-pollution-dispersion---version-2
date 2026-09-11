import pandas as pd
import os

def generate_festival_calendar(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, 'india_festivals.csv')
    
    if os.path.exists(out_file):
        print(f"File {out_file} already exists.")
        return out_file
        
    print("Generating major Indian festival calendar (2020-2025)...")
    
    # Hand-coded major dates for Diwali, which is the most significant pollution event
    events = [
        {'event_id': 1, 'event_name': 'Diwali', 'date': '2020-11-14', 'region': 'India', 'event_type': 'Festival'},
        {'event_id': 2, 'event_name': 'Diwali', 'date': '2021-11-04', 'region': 'India', 'event_type': 'Festival'},
        {'event_id': 3, 'event_name': 'Diwali', 'date': '2022-10-24', 'region': 'India', 'event_type': 'Festival'},
        {'event_id': 4, 'event_name': 'Diwali', 'date': '2023-11-12', 'region': 'India', 'event_type': 'Festival'},
        {'event_id': 5, 'event_name': 'Diwali', 'date': '2024-10-31', 'region': 'India', 'event_type': 'Festival'},
        {'event_id': 6, 'event_name': 'Diwali', 'date': '2025-10-20', 'region': 'India', 'event_type': 'Festival'}
    ]
    
    df = pd.DataFrame(events)
    df.to_csv(out_file, index=False)
    print(f"Saved festival calendar to {out_file}")
    return out_file

if __name__ == '__main__':
    generate_festival_calendar('data/raw/events')
