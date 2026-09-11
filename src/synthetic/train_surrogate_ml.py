"""
ML SURROGATE MODEL TRAINING
===========================
Trains a tabular Machine Learning surrogate model (RandomForestRegressor)
to reproduce the physics-derived 2D grid-to-grid dispersion relationships.

IMPORTANT NOTE:
The ML model is NOT the final pollution prediction objective.
It is being tested strictly as a surrogate / reproduction model
for the physics-derived dispersion relationship.

Splits Evaluated:
1. Random Train/Test Split (80/20)
2. Leave-One-City-Out (LOCO) Cross-Validation across all 10 cities
"""

import os
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DISCLAIMER = "SYNTHETIC DATA — PIPELINE/CONSTRAINT VERIFICATION ONLY"

FEATURE_COLS = [
    "source_lat", "source_lon",
    "dest_lat", "dest_lon",
    "rel_dx", "rel_dy",
    "u10", "v10", "wind_speed", "wind_direction_deg",
    "elapsed_time_hours", "source_pm25",
    "distance_km", "rel_angle_to_wind_deg"
]

TARGET_COL = "transport_influence"


def train_and_evaluate(data_dir="data/synthetic", models_dir="models", results_dir="results/ml"):
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    targets_path = os.path.join(data_dir, "transport_targets.csv")
    df = pd.read_csv(targets_path)
    print(f"[ML Surrogate] Loaded {len(df)} transport target samples.")

    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    # =========================================================================
    # 1. Random 80/20 Train / Test Split
    # =========================================================================
    np.random.seed(42)
    indices = np.arange(len(df))
    np.random.shuffle(indices)

    split_idx = int(0.8 * len(df))
    train_idx, test_idx = indices[:split_idx], indices[split_idx:]

    X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
    X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]

    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)

    y_pred_test = rf_model.predict(X_test)
    # Clamp negative predictions to 0 physically
    y_pred_test_clamped = np.maximum(0.0, y_pred_test)

    # Normalize ML transport fractions per group to strictly enforce mass conservation
    df_pred = df.copy()
    raw_ml_pred = np.maximum(0.0, rf_model.predict(X))
    df_pred["raw_ml_pred"] = raw_ml_pred

    # Groupwise normalization for ML predicted influence: sum(T_ml) <= sum(T_physics)
    group_sums = df_pred.groupby(["city_name", "timestamp_hour", "elapsed_time_hours"])["raw_ml_pred"].transform("sum")
    group_sums = np.where(group_sums == 0, 1.0, group_sums)
    df_pred["ml_predicted_influence"] = (df_pred["raw_ml_pred"] / group_sums) * df_pred["source_pm25"]

    mae = mean_absolute_error(y_test, y_pred_test_clamped)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test_clamped))
    r2 = r2_score(y_test, y_pred_test_clamped)

    print(f"[ML Surrogate] Random 80/20 Split Results -> MAE: {mae:.3f}, RMSE: {rmse:.3f}, R2: {r2:.4f}")

    # Save model
    model_path = os.path.join(models_dir, "surrogate_model.joblib")
    joblib.dump(rf_model, model_path)
    print(f"[ML Surrogate] Saved trained model artifact to: {model_path}")

    # Feature Importance
    feature_imp = pd.DataFrame({
        "feature": FEATURE_COLS,
        "importance": rf_model.feature_importances_
    }).sort_values("importance", ascending=False)
    feature_imp_path = os.path.join(results_dir, "feature_importances.csv")
    feature_imp.to_csv(feature_imp_path, index=False)

    # Save random split metrics
    metrics_df = pd.DataFrame([{
        "evaluation_split": "Random 80/20 Split",
        "sample_count": len(test_idx),
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2_score": round(r2, 4),
        "data_label": DISCLAIMER
    }])
    metrics_df.to_csv(os.path.join(results_dir, "ml_evaluation_metrics.csv"), index=False)

    # =========================================================================
    # 2. Leave-One-City-Out (LOCO) Cross-Validation
    # =========================================================================
    cities = df["city_name"].unique()
    loco_results = []

    for holdout_city in cities:
        loco_train_mask = (df["city_name"] != holdout_city)
        loco_test_mask = (df["city_name"] == holdout_city)

        X_loco_train, y_loco_train = X[loco_train_mask], y[loco_train_mask]
        X_loco_test, y_loco_test = X[loco_test_mask], y[loco_test_mask]

        model_loco = RandomForestRegressor(
            n_estimators=60,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model_loco.fit(X_loco_train, y_loco_train)

        y_loco_pred = np.maximum(0.0, model_loco.predict(X_loco_test))

        l_mae = mean_absolute_error(y_loco_test, y_loco_pred)
        l_rmse = np.sqrt(mean_squared_error(y_loco_test, y_loco_pred))
        l_r2 = r2_score(y_loco_test, y_loco_pred)

        loco_results.append({
            "holdout_city": holdout_city,
            "train_samples": len(X_loco_train),
            "test_samples": len(X_loco_test),
            "mae": round(l_mae, 4),
            "rmse": round(l_rmse, 4),
            "r2_score": round(l_r2, 4),
            "loco_status": "PASS" if l_r2 > 0.70 else "WARNING",
            "data_label": DISCLAIMER
        })

    loco_df = pd.DataFrame(loco_results)
    loco_path = os.path.join(results_dir, "loco_evaluation_metrics.csv")
    loco_df.to_csv(loco_path, index=False)
    print(f"[ML Surrogate] LOCO Cross-Validation Complete. Mean LOCO R2: {loco_df['r2_score'].mean():.4f}")

    return rf_model, metrics_df, loco_df


if __name__ == "__main__":
    train_and_evaluate()
