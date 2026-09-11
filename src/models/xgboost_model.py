import pandas as pd
import numpy as np
import xgboost as xgb
import argparse
import os
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score

def train_xgboost(features_csv, output_dir):
    print("Training XGBoost Residual Model...")
    os.makedirs(output_dir, exist_ok=True)
    out_model = os.path.join(output_dir, 'xgboost_residual_model.json')
    
    # Normally we load the compiled features dataset:
    # df = pd.read_csv(features_csv)
    # But since we're using dummy placeholder data for V1 migration...
    print("Generating dummy features for model pipeline test...")
    df = pd.DataFrame({
        'target_previous_year_AQI': np.random.uniform(50, 200, 100),
        'footprint_weight_sum': np.random.uniform(0.5, 1.0, 100),
        'wind_speed': np.random.uniform(0, 10, 100),
        'pblh': np.random.uniform(100, 2000, 100),
        'y_physics': np.random.normal(50, 10, 100),
        'y_observed': np.random.normal(55, 12, 100)
    })
    
    # Residual = Observed - Physics
    df['target_residual'] = df['y_observed'] - df['y_physics']
    
    X = df.drop(columns=['y_observed', 'y_physics', 'target_residual'])
    y = df['target_residual']
    
    # Temporal Split (mock)
    train_size = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
    
    model = xgb.XGBRegressor(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    
    print(f"Validation MAE: {mae:.2f}, R2: {r2:.2f}")
    
    model.save_model(out_model)
    print(f"Saved model to {out_model}")
    return out_model

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--features', type=str, default='data/processed/features.csv')
    parser.add_argument('--out_dir', type=str, default='src/models')
    args = parser.parse_args()
    
    train_xgboost(args.features, args.out_dir)
