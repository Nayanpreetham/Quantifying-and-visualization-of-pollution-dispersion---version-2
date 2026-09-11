"""
Train XGBoost baseline model using processed training data.
"""

import pandas as pd
import numpy as np
import joblib
import os
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

INPUT_CSV = "final clean/training_features_processed.csv"
MODEL_DIR = "Models"

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    print("Loading processed data...")
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} rows")

    # Identify which features are actually in the dataset
    potential_features = [
        't2m', 'wind_speed', 'humidity_pct', 'sp_hpa', 'blh', 'tp_mm',
        'elevation_m', 'elevation_pblh_ratio', 'stagnation_index',
        'dispersion_potential', 'terrain_blocking_score', 'ventilation_index',
        'wind_dir_sin', 'wind_dir_cos', 'month_sin', 'month_cos'
    ]

    # Filter to features that actually exist
    FEATURE_COLS = [f for f in potential_features if f in df.columns]
    print(f"\nUsing {len(FEATURE_COLS)} features:")
    for f in FEATURE_COLS:
        print(f"  - {f}")

    # Drop rows with NaN in features or target
    df = df.dropna(subset=FEATURE_COLS + ['aqi'])
    print(f"\nAfter dropping NaNs: {len(df)} samples")

    X = df[FEATURE_COLS]
    y = df['aqi']

    print(f"Training on {len(X)} samples, {len(FEATURE_COLS)} features")

    # Temporal split (80% train, 20% test)
    split_idx = int(0.8 * len(df))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train XGBoost
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X_train_scaled, y_train)

    # Evaluate
    train_score = model.score(X_train_scaled, y_train)
    test_score = model.score(X_test_scaled, y_test)
    print(f"\nTrain R²: {train_score:.3f}, Test R²: {test_score:.3f}")

    # Save artifacts
    joblib.dump(model, f"{MODEL_DIR}/aqi_baseline_model.pkl")
    joblib.dump(scaler, f"{MODEL_DIR}/scaler.pkl")
    joblib.dump(FEATURE_COLS, f"{MODEL_DIR}/feature_columns.pkl")

    # Save feature importance
    importance = pd.DataFrame({
        'feature': FEATURE_COLS,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    importance.to_csv(f"{MODEL_DIR}/feature_importance.csv", index=False)
    print("\nFeature Importance (top 10):")
    print(importance.head(10).to_string(index=False))

    print(f"\n✅ Model saved to {MODEL_DIR}/")

if __name__ == "__main__":
    main()