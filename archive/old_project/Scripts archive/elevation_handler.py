import rasterio
import pandas as pd
import numpy as np
import os
from rasterio.sample import sample_gen
from scipy.spatial import cKDTree

PROJECT = r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project"
DEM_FILE = os.path.join(PROJECT, "india_dem.tif")
OUTPUT_FOLDER = os.path.join(PROJECT, "output")

print("Loading data...")
df = pd.read_csv(os.path.join(OUTPUT_FOLDER, "aqi_era5_merged.csv"))

# Get unique cities with coordinates
cities = df[['city', 'lat', 'lon']].drop_duplicates().reset_index(drop=True)
print(f"Processing {len(cities)} cities...")

# Step 1: Extract elevations from DEM where possible
print("\n📡 Extracting elevations from DEM...")
elevations = []

with rasterio.open(DEM_FILE) as dem:
    for idx, row in cities.iterrows():
        lon, lat = row['lon'], row['lat']
        
        try:
            # Sample elevation at point
            samples = list(sample_gen(dem, [(lon, lat)]))
            elev = samples[0][0]
            
            # Check if valid (not NoData)
            if elev is not None and not np.isnan(elev) and elev != dem.nodata and elev > -1000:
                elevations.append({
                    'city': row['city'],
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'elevation_m': float(elev),
                    'elevation_source': 'exact_dem'
                })
            else:
                elevations.append({
                    'city': row['city'],
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'elevation_m': np.nan,
                    'elevation_source': 'missing'
                })
        except Exception as e:
            elevations.append({
                'city': row['city'],
                'lat': row['lat'],
                'lon': row['lon'],
                'elevation_m': np.nan,
                'elevation_source': 'error'
            })
        
        if (idx + 1) % 50 == 0:
            print(f"  Processed {idx+1}/{len(cities)} cities...")

elev_df = pd.DataFrame(elevations)
print(f"\n✅ Initial extraction complete")
print(f"  Success: {(~elev_df['elevation_m'].isna()).sum()} cities")
print(f"  Missing: {elev_df['elevation_m'].isna().sum()} cities")

# Step 2: Handle missing elevations using nearest neighbor
missing_mask = elev_df['elevation_m'].isna()
if missing_mask.any():
    print(f"\n🔧 Filling {missing_mask.sum()} missing cities using nearest neighbor...")
    
    # Get cities with valid elevations
    valid_df = elev_df[~missing_mask].copy()
    valid_coords = valid_df[['lat', 'lon']].values
    valid_elevs = valid_df['elevation_m'].values
    
    # Build KD-tree for fast nearest neighbor search
    if len(valid_coords) > 0:
        tree = cKDTree(valid_coords)
        
        # Fill missing values
        for idx in elev_df[missing_mask].index:
            lat = elev_df.loc[idx, 'lat']
            lon = elev_df.loc[idx, 'lon']
            
            # Find nearest city with elevation data
            dist, nearest_idx = tree.query([lat, lon])
            
            if dist < 2.0:  # Within 2 degrees (~220 km)
                elev_df.loc[idx, 'elevation_m'] = valid_elevs[nearest_idx]
                elev_df.loc[idx, 'elevation_source'] = f'nearest_city_{dist:.2f}deg'
            else:
                # Use regional average
                elev_df.loc[idx, 'elevation_m'] = valid_elevs.mean()
                elev_df.loc[idx, 'elevation_source'] = 'regional_avg'

# Step 3: Merge back to main dataframe
print("\n📊 Merging elevation data...")
df = df.merge(elev_df[['city', 'elevation_m', 'elevation_source']], on='city', how='left')

# Step 4: Add derived elevation features
print("\n🔧 Creating elevation-based features...")

# Terrain category
df['terrain_category'] = pd.cut(df['elevation_m'], 
                                 bins=[0, 200, 500, 1000, 10000],
                                 labels=['lowland', 'midland', 'highland', 'mountain'])

# Elevation-PBLH interaction (trapping potential)
df['elevation_pblh_ratio'] = df['elevation_m'] / (df['blh'] + 1)

# Terrain blocking score
df['terrain_blocking_score'] = np.clip(
    (df['elevation_m'] / 1000) * (1 - df['wind_speed'] / 10),
    0, 1
)

# Stagnation index
df['stagnation_index'] = np.clip(
    (df['terrain_blocking_score'] * 0.5) + 
    ((1 - df['wind_speed'] / 8) * 0.5),
    0, 1
)

# Dispersion potential
df['dispersion_potential'] = 1 - df['stagnation_index']

# Step 5: Save final dataset
output_file = os.path.join(OUTPUT_FOLDER, "aqi_era5_elevation_enhanced.csv")
df.to_csv(output_file, index=False)

# Summary statistics
print("\n" + "=" * 60)
print("✅ COMPLETE! Enhanced dataset created")
print("=" * 60)
print(f"\n📁 Saved to: {output_file}")
print(f"📊 Shape: {df.shape}")
print(f"📋 Total columns: {len(df.columns)}")

print("\n📊 Elevation Statistics:")
print(f"  Min: {df['elevation_m'].min():.1f}m")
print(f"  Max: {df['elevation_m'].max():.1f}m")
print(f"  Mean: {df['elevation_m'].mean():.1f}m")
print(f"  Median: {df['elevation_m'].median():.1f}m")

print("\n📊 Elevation Sources:")
source_counts = df['elevation_source'].value_counts()
for source, count in source_counts.items():
    print(f"  {source}: {count} rows")

print("\n📍 Missing Cities Check:")
missing_cities = elev_df[elev_df['elevation_source'].str.contains('missing|error', na=False)]
if len(missing_cities) > 0:
    print(f"  WARNING: {len(missing_cities)} cities still missing elevation")
    for _, row in missing_cities.iterrows():
        print(f"    - {row['city']}")
else:
    print("  ✓ All cities have elevation data!")

print("\n📈 New Features Added:")
new_features = ['elevation_m', 'terrain_category', 'elevation_pblh_ratio', 
                'terrain_blocking_score', 'stagnation_index', 'dispersion_potential']
for feat in new_features:
    print(f"  ✓ {feat}")

# Optional: Show correlation with AQI
print("\n📊 Correlation with AQI:")
corr_vars = ['aqi', 'elevation_m', 'elevation_pblh_ratio', 'terrain_blocking_score', 'stagnation_index']
corr_matrix = df[corr_vars].corr()['aqi'].sort_values(ascending=False)
for var, corr in corr_matrix.items():
    if var != 'aqi':
        print(f"  {var}: {corr:.3f}")

print("\n✅ Ready for machine learning!")