# Copy this entire script as 'eda_baseline.py'

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Load data
df = pd.read_csv('output/aqi_era5_elevation_enhanced.csv')

# Features
feature_cols = ['t2m', 'wind_speed', 'humidity_pct', 'sp_hpa', 'blh', 
                'tp_mm', 'elevation_m', 'elevation_pblh_ratio', 
                'terrain_blocking_score', 'stagnation_index']

print("="*60)
print("STEP 1: FEATURE IMPORTANCE")
print("="*60)

X = df[feature_cols]
y = df['aqi']

rf = RandomForestRegressor(n_estimators=100, random_state=42)
rf.fit(X, y)

importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)

print(importance.to_string(index=False))
print(f"\nTop feature: {importance.iloc[0]['feature']} ({importance.iloc[0]['importance']:.1%})")

print("\n" + "="*60)
print("STEP 2: VISUALIZATIONS")
print("="*60)

fig, axes = plt.subplots(1, 2, figsize=(12, 4))

# Stagnation vs AQI
sns.scatterplot(data=df.sample(5000), x='stagnation_index', y='aqi', alpha=0.5, ax=axes[0])
axes[0].set_title('Stagnation Index vs AQI')
axes[0].set_xlabel('Stagnation Index')
axes[0].set_ylabel('AQI')

# Terrain categories
sns.boxplot(data=df, x='terrain_category', y='aqi', ax=axes[1])
axes[1].set_title('AQI by Terrain Type')
axes[1].set_xlabel('Terrain Category')
axes[1].set_ylabel('AQI')
plt.xticks(rotation=45)

plt.tight_layout()
plt.savefig('output/eda_plots.png', dpi=150, bbox_inches='tight')
plt.show()

print("\n" + "="*60)
print("STEP 3: BASELINE MODEL (Random Forest)")
print("="*60)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"MAE: {mae:.2f} AQI points")
print(f"R² Score: {r2:.3f}")
print(f"\nInterpretation: Model explains {r2*100:.1f}% of AQI variance")
print(f"Average prediction error: ±{mae:.1f} AQI points")

print("\n" + "="*60)
print("READY FOR XGBOOST!")
print("="*60)
print("Baseline established. XGBoost should achieve:")
print(f"  - MAE < {mae:.2f}")
print(f"  - R² > {r2:.3f}")