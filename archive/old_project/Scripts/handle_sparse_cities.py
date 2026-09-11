"""
Handle sparse cities (10 cities with <100 AQI readings)
Using sample weights instead of dropping them
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# Paths
PROJECT = Path(r"C:\Users\Nayan preetham\OneDrive\Documents\UG project\Aqi prediction project")
FINAL_DIR = PROJECT / "final clean"
INTERMEDIATE_DIR = PROJECT / "intermediate"

# Load the final clean dataset
df = pd.read_csv(FINAL_DIR / "aqi_final_clean.csv")

print("="*60)
print("SPARSE CITIES HANDLING WITH SAMPLE WEIGHTS")
print("="*60)

# ============================================================================
# 1. IDENTIFY SPARSE CITIES
# ============================================================================
print("\n📊 Step 1: Identifying sparse cities...")

city_counts = df['city'].value_counts()
sparse_cities = city_counts[city_counts < 100].index.tolist()
dense_cities = city_counts[city_counts >= 100].index.tolist()

print(f"\n  Total cities: {len(city_counts)}")
print(f"  Dense cities (≥100 rows): {len(dense_cities)}")
print(f"  Sparse cities (<100 rows): {len(sparse_cities)}")

print(f"\n  Sparse cities with row counts:")
for city in sorted(sparse_cities):
    count = city_counts[city]
    print(f"    • {city:<25} : {count:3} rows")

# ============================================================================
# 2. CALCULATE SAMPLE WEIGHTS
# ============================================================================
print("\n📊 Step 2: Calculating sample weights...")

# Method: Inverse frequency weighting
# Weight = 1 / (city_row_count / max_row_count)
# This gives:
#   - Cities with many rows get low weight
#   - Cities with few rows get high weight
#   - Normalized so total weight = number of samples

max_count = city_counts.max()  # Howrah has 1461 rows

# Calculate raw weights (inverse frequency)
df['raw_weight'] = max_count / df['city'].map(city_counts)

# Normalize so average weight = 1
df['sample_weight'] = df['raw_weight'] / df['raw_weight'].mean()

print(f"\n  Weight statistics:")
print(f"    Min weight: {df['sample_weight'].min():.3f}")
print(f"    Max weight: {df['sample_weight'].max():.3f}")
print(f"    Mean weight: {df['sample_weight'].mean():.3f}")

# Show weight distribution by city type
print(f"\n  Average weight by city type:")
sparse_mask = df['city'].isin(sparse_cities)
print(f"    Sparse cities (<100 rows): {df[sparse_mask]['sample_weight'].mean():.3f}")
print(f"    Dense cities (≥100 rows): {df[~sparse_mask]['sample_weight'].mean():.3f}")

# Show specific examples
print(f"\n  Example weights for specific cities:")
example_cities = ['Howrah', 'Delhi', 'Tiruchirappalli', 'Karwar']
for city in example_cities:
    if city in df['city'].values:
        weight = df[df['city'] == city]['sample_weight'].iloc[0]
        rows = city_counts[city]
        print(f"    • {city:<20} : {rows:4} rows → weight = {weight:.4f}")

# ============================================================================
# 3. VALIDATE WEIGHT DISTRIBUTION
# ============================================================================
print("\n📊 Step 3: Validating weights...")

# Check total weight sum
total_weight = df['sample_weight'].sum()
print(f"  Total weight sum: {total_weight:.1f}")
print(f"  Number of samples: {len(df)}")
print(f"  Ratio (should be ~1): {total_weight/len(df):.3f}")

# ============================================================================
# 4. CAP OUTLIERS IN FEATURES (Before ML)
# ============================================================================
print("\n📊 Step 4: Capping extreme outliers...")

# terrain_blocking_score has insane max (17,288)
outlier_cols = ['terrain_blocking_score', 'ventilation_index', 'dispersion_potential']

for col in outlier_cols:
    if col in df.columns:
        before_max = df[col].max()
        # Cap at 99th percentile
        cap = df[col].quantile(0.99)
        df[col] = df[col].clip(upper=cap)
        after_max = df[col].max()
        print(f"  {col}: capped from {before_max:.2f} → {after_max:.2f}")

# ============================================================================
# 5. CREATE FINAL ML-READY DATASET
# ============================================================================
print("\n📊 Step 5: Creating final ML-ready dataset...")

# Select features for modeling
feature_cols = [
    't2m', 'wind_speed', 'humidity_pct', 'sp_hpa', 'blh', 'tp_mm',
    'elevation_m', 'elevation_pblh_ratio', 'stagnation_index',
    'dispersion_potential', 'terrain_blocking_score', 'ventilation_index'
]

# Verify all features exist
missing_features = [f for f in feature_cols if f not in df.columns]
if missing_features:
    print(f"⚠ Warning: Missing features: {missing_features}")
else:
    print(f"  ✅ All {len(feature_cols)} features available")

# Create ML-ready dataset
ml_df = df[['date', 'city', 'lat', 'lon', 'aqi'] + feature_cols + ['sample_weight']].copy()

print(f"\n  Final dataset shape: {ml_df.shape}")
print(f"  Columns: {ml_df.columns.tolist()}")

# ============================================================================
# 6. SAVE DATASETS
# ============================================================================
print("\n📊 Step 6: Saving datasets...")

# Save the enhanced dataset with weights
output_path = FINAL_DIR / "aqi_final_clean_weighted.csv"
ml_df.to_csv(output_path, index=False)
print(f"  ✅ Saved: {output_path}")
print(f"     Size: {len(ml_df):,} rows × {len(ml_df.columns)} columns")

# Also save the weights reference separately
weight_summary = pd.DataFrame({
    'city': city_counts.index,
    'row_count': city_counts.values,
    'sample_weight': [df[df['city'] == c]['sample_weight'].iloc[0] for c in city_counts.index]
}).sort_values('sample_weight', ascending=False)

weight_path = FINAL_DIR / "city_sample_weights.csv"
weight_summary.to_csv(weight_path, index=False)
print(f"  ✅ Saved: {weight_path}")

# ============================================================================
# 7. SUMMARY REPORT
# ============================================================================
print("\n" + "="*60)
print("✅ SPARSE CITIES HANDLED - SUMMARY")
print("="*60)

print(f"""
┌─────────────────────────────────────────────────────────────────┐
│                    SAMPLE WEIGHT STRATEGY                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Total cities:        {len(city_counts):3}                                     │
│  Total rows:          {len(df):,}                                   │
│  Sparse cities:       {len(sparse_cities):2} (kept with higher weight)        │
│                                                                 │
│  Weight range:        {df['sample_weight'].min():.3f} - {df['sample_weight'].max():.3f}                    │
│                                                                 │
│  How it works:                                                 │
│  • Cities with FEW rows get HIGHER weight (learn more from each row)│
│  • Cities with MANY rows get LOWER weight (avoid overfitting)  │
│  • Total weighted samples = {total_weight:.0f} (same as actual rows)        │
│                                                                 │
│  During training:                                              │
│  model.fit(X, y, sample_weight=df['sample_weight'])            │
│                                                                 │
│  This preserves spatial coverage while preventing overfitting  │
│  on sparse cities!                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
""")

# List sparse cities with their weights
print("\n📋 Sparse cities with assigned weights:")
sparse_summary = weight_summary[weight_summary['city'].isin(sparse_cities)].sort_values('row_count')
for _, row in sparse_summary.iterrows():
    print(f"    {row['city']:<25} : {int(row['row_count']):3} rows → weight = {row['sample_weight']:.4f}")

print("\n" + "="*60)
print("✅ READY FOR MODEL TRAINING!")
print("="*60)
print(f"""
Next step: Train XGBoost with sample weights

Use this dataset: {output_path}
Use weight column: sample_weight

Example:
    df = pd.read_csv('{output_path}')
    X = df[feature_cols]
    y = df['aqi']
    weights = df['sample_weight']
    
    model.fit(X, y, sample_weight=weights)
""")