"""
ML Training Script — standalone runner.
Run from project root:
    python ml/train_model.py

This script:
1. Loads the Flask app context.
2. Reads sales data from MySQL.
3. Preprocesses features.
4. Trains RandomForestRegressor.
5. Evaluates on chronological test split.
6. Saves model and metadata to trained_models/.
7. Optionally plots evaluation charts.
"""

import os
import sys
import json
from datetime import datetime

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for script use
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


MODEL_DIR = os.path.join(PROJECT_ROOT, 'trained_models')


def train():
    print("=" * 60)
    print("RetailTwin AI — ML Training Script")
    print("=" * 60)

    # Flask context needed for database access
    from app import create_app
    app = create_app()

    with app.app_context():
        from ml.preprocessor import build_global_training_set

        print("\n[1/6] Loading and preprocessing data...")
        df = build_global_training_set()

        if df is None or df.empty:
            print("[ERROR] No sales data found. Please seed the database first.")
            sys.exit(1)

        print(f"  Loaded {len(df)} training samples from {df['product_id'].nunique()} products "
              f"across {df['store_id'].nunique()} stores.")

        min_required = app.config.get('ML_MIN_RECORDS', 30)
        if len(df) < min_required:
            print(f"[ERROR] Only {len(df)} records available. At least {min_required} needed.")
            print("  Record more sales and re-run this script.")
            sys.exit(1)

        feature_cols = [
            'product_id', 'store_id', 'day_of_week', 'day_of_month', 'month',
            'is_weekend', 'week_of_year', 'selling_price', 'discount',
            'lag_7', 'lag_14', 'lag_30', 'rolling_mean_7', 'rolling_mean_14', 'rolling_std_7'
        ]
        available_cols = [c for c in feature_cols if c in df.columns]

        X = df[available_cols]
        y = df['quantity_sold']

        # Chronological split — NO random shuffling (prevents data leakage)
        split_idx  = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        print(f"  Train: {len(X_train)} samples | Test: {len(X_test)} samples (chronological)")

        # --- Train RandomForestRegressor ---
        print("\n[2/6] Training RandomForestRegressor...")
        rf = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1, min_samples_leaf=2)
        rf.fit(X_train, y_train)
        y_pred_rf = rf.predict(X_test)

        rf_mae  = mean_absolute_error(y_test, y_pred_rf)
        rf_rmse = np.sqrt(mean_squared_error(y_test, y_pred_rf))
        rf_r2   = r2_score(y_test, y_pred_rf)
        rf_quality = max(0.0, rf_r2) * 100

        print(f"  RandomForest — MAE: {rf_mae:.4f} | RMSE: {rf_rmse:.4f} | R²: {rf_r2:.4f}")
        print(f"  Model Quality Score: {rf_quality:.1f}%")

        # --- Baseline LinearRegression ---
        print("\n[3/6] Training baseline LinearRegression...")
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        y_pred_lr = lr.predict(X_test)
        lr_mae  = mean_absolute_error(y_test, y_pred_lr)
        lr_rmse = np.sqrt(mean_squared_error(y_test, y_pred_lr))
        lr_r2   = r2_score(y_test, y_pred_lr)
        print(f"  LinearRegression — MAE: {lr_mae:.4f} | RMSE: {lr_rmse:.4f} | R²: {lr_r2:.4f}")

        # --- Save RandomForest (primary model) ---
        print("\n[4/6] Saving model...")
        os.makedirs(MODEL_DIR, exist_ok=True)
        model_path = os.path.join(MODEL_DIR, 'demand_forecast_rf.pkl')
        joblib.dump(rf, model_path)
        print(f"  Model saved: {model_path}")

        # Save metadata
        metadata = {
            'model_name':     'RandomForestRegressor',
            'trained_at':     datetime.utcnow().isoformat(),
            'n_samples':      len(df),
            'n_train':        len(X_train),
            'n_test':         len(X_test),
            'feature_columns': available_cols,
            'metrics': {
                'MAE':           round(rf_mae, 4),
                'RMSE':          round(rf_rmse, 4),
                'R2':            round(rf_r2, 4),
                'quality_score': round(rf_quality, 2),
            },
            'baseline_metrics': {
                'model':  'LinearRegression',
                'MAE':    round(lr_mae, 4),
                'RMSE':   round(lr_rmse, 4),
                'R2':     round(lr_r2, 4),
            }
        }
        meta_path = os.path.join(MODEL_DIR, 'model_metadata.json')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  Metadata saved: {meta_path}")

        # --- Feature importance ---
        print("\n[5/6] Feature importances:")
        importances = pd.Series(rf.feature_importances_, index=available_cols).sort_values(ascending=False)
        for feat, imp in importances.items():
            print(f"  {feat:30s}: {imp:.4f}")

        # --- Evaluation plot ---
        print("\n[6/6] Saving evaluation chart...")
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # Actual vs Predicted
        axes[0].scatter(y_test, y_pred_rf, alpha=0.5, color='steelblue', s=20)
        axes[0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=1.5)
        axes[0].set_xlabel('Actual Demand')
        axes[0].set_ylabel('Predicted Demand')
        axes[0].set_title(f'RF: Actual vs Predicted (R²={rf_r2:.3f})')

        # Residuals
        residuals = y_test.values - y_pred_rf
        axes[1].hist(residuals, bins=20, color='steelblue', edgecolor='white')
        axes[1].set_xlabel('Residual (Actual - Predicted)')
        axes[1].set_ylabel('Count')
        axes[1].set_title('Residual Distribution')

        plt.tight_layout()
        plot_path = os.path.join(MODEL_DIR, 'evaluation_plot.png')
        plt.savefig(plot_path, dpi=100)
        plt.close()
        print(f"  Plot saved: {plot_path}")

    print("\n" + "=" * 60)
    print("Training COMPLETE")
    print(f"  RandomForest Quality Score: {rf_quality:.1f}%")
    print(f"  Baseline (LinearReg) R²:    {lr_r2:.4f}")
    if rf_r2 > lr_r2:
        print(f"  RandomForest outperforms baseline by {(rf_r2 - lr_r2)*100:.2f}% R² points.")
    print("=" * 60)


if __name__ == '__main__':
    train()
