import requests
from bs4 import BeautifulSoup
import os
import urllib.parse

url = "https://urbanemissions.info/india-air-quality/india-ncap-aqi-indian-cities-2015-2023/"
base_url = "https://urbanemissions.info"

# Create folder
os.makedirs("aqi_data", exist_ok=True)

# Headers to mimic browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Get page
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

# Find all CSV links safely
links = soup.find_all("a")
csv_links = [link.get("href") for link in links if not isinstance(link, str) and link.get("href") and link.get("href").endswith('.csv')]

print(f"Found {len(csv_links)} CSV files.")
print("CSV hrefs:")
for href in csv_links:
    print(f"  - {href}")

if not csv_links:
    print("No CSV links found. Check the website manually.")
else:
    # Download all CSVs
    for i, link in enumerate(csv_links):
        try:
            file_url = urllib.parse.urljoin(base_url, link)
            parsed = urllib.parse.urlparse(file_url)
            file_name = os.path.basename(parsed.path)
            if not file_name or not file_name.endswith('.csv'):
                file_name = f'aqi_city_{i}.csv'

            print(f"Downloading {i+1}/{len(csv_links)}: {file_name} from {file_url}")

            r = requests.get(file_url, headers=headers)
            r.raise_for_status()

            with open(os.path.join("aqi_data", file_name), "wb") as f:
                f.write(r.content)

            print(f"  ✓ Saved {file_name}")

        except Exception as e:
            print(f"  ✗ Failed {link}: {e}")

print("All downloads attempted. Check aqi_data/ folder.")

