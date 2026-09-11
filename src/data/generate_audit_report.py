import pandas as pd
import ast

df = pd.read_csv('data/interim/openaq_in_locations.csv')

def parse_sensors(s):
    try:
        return ast.literal_eval(s)
    except:
        return []

df['sensors_list'] = df['sensors'].apply(parse_sensors)

has_pm25 = lambda sensors: any(s['parameter']['name'] == 'pm25' for s in sensors)
has_pm10 = lambda sensors: any(s['parameter']['name'] == 'pm10' for s in sensors)

df['has_pm25'] = df['sensors_list'].apply(has_pm25)
df['has_pm10'] = df['sensors_list'].apply(has_pm10)

df['first_dt'] = pd.to_datetime(df['datetimeFirst.utc'], errors='coerce')
df['last_dt'] = pd.to_datetime(df['datetimeLast.utc'], errors='coerce')
df['duration_days'] = (df['last_dt'] - df['first_dt']).dt.days

cpcb_mask = df['provider.name'].str.contains('CPCB|Central Pollution', na=False, case=False)

print("="*50)
print("OPENAQ vs CPCB COVERAGE AUDIT")
print("="*50)

print(f"Total OpenAQ Stations in India: {len(df)}")
print(f"Total CPCB Official Stations in OpenAQ: {cpcb_mask.sum()}")
print(f"Estimated Missing CPCB Stations: ~{max(0, 500 - cpcb_mask.sum())}")

print("\n--- Coverage by State/Locality ---")
print(df['locality'].value_counts().head(10))

print("\n--- Coverage by Pollutant ---")
print(f"PM2.5 Stations: {df['has_pm25'].sum()} ({df['has_pm25'].sum()/len(df)*100:.1f}%)")
print(f"PM10 Stations: {df['has_pm10'].sum()} ({df['has_pm10'].sum()/len(df)*100:.1f}%)")

print("\n--- Coverage by Year (First Observation) ---")
print(df['first_dt'].dt.year.value_counts().sort_index())

print("\n--- Hourly Observation Availability ---")
# If it's been active for > 365 days, we consider it a 'long-term hourly' station in OpenAQ
long_term = (df['duration_days'] > 365).sum()
print(f"Stations with > 1 year of continuous/hourly data history: {long_term}")

