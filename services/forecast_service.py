"""
Demand Forecast Service.
Coordinates ML preprocessing, model training, and prediction generation.
Handles the small-dataset fallback gracefully.
"""

import os
import json
from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import numpy as np

from models import db
from models.sales import Sales
from models.demand_forecast import DemandForecast
from models.product import Product
from models.store import Store


# Minimum sales records required before attempting ML training
ML_MIN_RECORDS = int(os.environ.get('ML_MIN_RECORDS', 14))
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'trained_models')


def _load_sales_df(product_id: int, store_id: int) -> pd.DataFrame:
    """Load historical sales for a product/store pair as a DataFrame."""
    sales = Sales.query.filter_by(
        product_id=product_id, store_id=store_id
    ).order_by(Sales.sale_date).all()

    if not sales:
        return pd.DataFrame()

    rows = [{
        'sale_date':    s.sale_date,
        'quantity_sold': s.quantity_sold,
        'selling_price': float(s.selling_price),
        'discount':      float(s.discount),
        'revenue':       float(s.revenue),
    } for s in sales]

    df = pd.DataFrame(rows)
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    df = df.sort_values('sale_date').reset_index(drop=True)
    return df


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering for demand forecasting on a single product/store time series.
    Creates time, lag, and rolling features without data leakage.
    """
    df = df.copy()
    df['day_of_week'] = df['sale_date'].dt.dayofweek
    df['day_of_month'] = df['sale_date'].dt.day
    df['month'] = df['sale_date'].dt.month
    df['quarter'] = df['sale_date'].dt.quarter
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['week_of_year'] = df['sale_date'].dt.isocalendar().week.astype(int)

    # Lag features
    df['lag_1']  = df['quantity_sold'].shift(1)
    df['lag_2']  = df['quantity_sold'].shift(2)
    df['lag_3']  = df['quantity_sold'].shift(3)
    df['lag_7']  = df['quantity_sold'].shift(7)
    df['lag_14'] = df['quantity_sold'].shift(14)
    df['lag_21'] = df['quantity_sold'].shift(21)
    df['lag_28'] = df['quantity_sold'].shift(28)

    # Rolling statistics
    df['rolling_mean_3']  = df['quantity_sold'].shift(1).rolling(3,  min_periods=1).mean()
    df['rolling_mean_7']  = df['quantity_sold'].shift(1).rolling(7,  min_periods=1).mean()
    df['rolling_mean_14'] = df['quantity_sold'].shift(1).rolling(14, min_periods=1).mean()
    df['rolling_mean_28'] = df['quantity_sold'].shift(1).rolling(28, min_periods=1).mean()
    
    df['rolling_std_7']   = df['quantity_sold'].shift(1).rolling(7,  min_periods=1).std()
    df['rolling_std_14']  = df['quantity_sold'].shift(1).rolling(14, min_periods=1).std()
    df['rolling_std_28']  = df['quantity_sold'].shift(1).rolling(28, min_periods=1).std()

    # Fill NaNs with 0 to match preprocessor
    df = df.fillna(0).reset_index(drop=True)
    return df


def _moving_average_forecast(df: pd.DataFrame, periods: int = 7) -> float:
    """
    Simple baseline: mean of last N days of quantity_sold.
    """
    if df.empty:
        return 0.0
    recent = df['quantity_sold'].tail(periods)
    return round(float(recent.mean()), 2)


def train_model() -> dict:
    """
    Evaluate multiple ML models on available sales data.
    Selects best based on Walk-Forward Validation.
    """
    import joblib
    from sklearn.ensemble import (
        RandomForestRegressor, 
        ExtraTreesRegressor, 
        GradientBoostingRegressor,
        HistGradientBoostingRegressor
    )
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from ml.preprocessor import build_global_training_set

    try:
        df = build_global_training_set()

        if df is None or df.empty:
            return {'success': False, 'message': 'No sales data available for training.'}

        if len(df) < ML_MIN_RECORDS:
            return {
                'success': False,
                'message': (f'Only {len(df)} records available. '
                            f'At least {ML_MIN_RECORDS} are needed for ML training. '
                            f'Record more sales or use the baseline forecasting mode.')
            }

        feature_cols = [
            'product_id', 'store_id', 'day_of_week', 'day_of_month', 'month', 'quarter',
            'is_weekend', 'week_of_year', 'selling_price', 'discount',
            'lag_1', 'lag_2', 'lag_3', 'lag_7', 'lag_14', 'lag_21', 'lag_28', 
            'rolling_mean_3', 'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_28', 
            'rolling_std_7', 'rolling_std_14', 'rolling_std_28'
        ]

        available_cols = [c for c in feature_cols if c in df.columns]
        X = df[available_cols]
        y = df['quantity_sold']

        # Chronological split — no random shuffling
        split_idx = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        if len(X_train) < 10 or len(X_test) < 2:
            return {'success': False, 'message': 'Insufficient data for train/test split.'}

        candidates = {
            'RandomForestRegressor': RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            'ExtraTreesRegressor': ExtraTreesRegressor(n_estimators=100, random_state=42, n_jobs=-1),
            'GradientBoostingRegressor': GradientBoostingRegressor(random_state=42),
            'HistGradientBoostingRegressor': HistGradientBoostingRegressor(random_state=42)
        }

        best_model = None
        best_name = None
        best_metrics = None
        best_rmse = float('inf')
        
        comparison = []

        for name, model in candidates.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            
            mae  = float(mean_absolute_error(y_test, y_pred))
            rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
            r2   = float(r2_score(y_test, y_pred))
            
            comparison.append({
                'model': name,
                'mae': round(mae, 4),
                'rmse': round(rmse, 4),
                'r2': round(r2, 4)
            })

            if rmse < best_rmse:
                best_rmse = rmse
                best_name = name
                best_model = model
                best_metrics = {
                    'MAE': round(mae, 4),
                    'RMSE': round(rmse, 4),
                    'R2': round(r2, 4),
                    'quality_score': round(max(0.0, r2) * 100, 2)
                }

        # Save best model
        os.makedirs(MODEL_DIR, exist_ok=True)
        model_path = os.path.join(MODEL_DIR, 'demand_forecast_best.pkl')
        joblib.dump(best_model, model_path)

        metadata = {
            'model_name':      best_name,
            'trained_at':      datetime.utcnow().isoformat(),
            'n_samples':       len(df),
            'n_train':         len(X_train),
            'n_test':          len(X_test),
            'feature_columns': available_cols,
            'metrics':         best_metrics,
            'comparison':      comparison
        }
        meta_path = os.path.join(MODEL_DIR, 'model_metadata.json')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return {
            'success': True,
            'message': f'Model {best_name} trained successfully.',
            'metrics': best_metrics,
            'model_name': best_name,
            'n_samples': len(df),
            'comparison': comparison
        }

    except Exception as e:
        return {'success': False, 'message': f'Training failed: {str(e)}'}


def generate_forecast(product_id: int, store_id: int, forecast_date_str: str, save: bool = True) -> dict:
    """
    Generate demand forecast recursively for requested date.
    """
    import joblib

    try:
        forecast_date = date.fromisoformat(forecast_date_str)
    except ValueError:
        return {'success': False, 'message': 'Invalid date format. Use YYYY-MM-DD.'}

    product = Product.query.get(product_id)
    store   = Store.query.get(store_id)
    if not product or not store:
        return {'success': False, 'message': 'Product or store not found.'}

    df = _load_sales_df(product_id, store_id)

    model_path = os.path.join(MODEL_DIR, 'demand_forecast_best.pkl')
    meta_path  = os.path.join(MODEL_DIR, 'model_metadata.json')

    model_used     = 'BaselineMovingAverage'
    quality_score  = 0.0
    model_metadata = None
    predicted      = 0.0
    
    today = date.today()
    if not df.empty:
        last_date = df['sale_date'].max().date()
    else:
        last_date = today - timedelta(days=1)

    if os.path.exists(model_path) and os.path.exists(meta_path):
        with open(meta_path) as f:
            model_metadata = json.load(f)

        quality_score  = model_metadata.get('metrics', {}).get('quality_score', 0.0)
        feature_cols   = model_metadata.get('feature_columns', [])
        model_used     = model_metadata.get('model_name', 'RandomForestRegressor')

        if df.empty or len(df) < 7:
            # Fallback
            predicted = _moving_average_forecast(df)
            model_used = 'BaselineMovingAverage'
        else:
            try:
                ml_model = joblib.load(model_path)
                
                # Recursive multi-day forecasting
                current_date = last_date + timedelta(days=1)
                
                # If target is in the past or today, we still need to project up to it 
                # (or if it's already in df, we could just return the actual, but let's forecast)
                if forecast_date <= last_date:
                    current_date = forecast_date
                    
                temp_df = df.copy()
                
                while current_date <= forecast_date:
                    feat_df = _build_features(temp_df)
                    last_row = feat_df.iloc[-1].copy()
                    
                    fd = pd.Timestamp(current_date)
                    
                    row = {
                        'product_id':       product_id,
                        'store_id':         store_id,
                        'day_of_week':      fd.dayofweek,
                        'day_of_month':     fd.day,
                        'month':            fd.month,
                        'quarter':          fd.quarter,
                        'is_weekend':       int(fd.dayofweek >= 5),
                        'week_of_year':     fd.isocalendar()[1],
                        'selling_price':    float(product.selling_price),
                        'discount':         0.0,
                    }
                    
                    # Fill lags from the *last_row* of the newly built features, because
                    # we want the lag relative to the new current_date.
                    # Wait, if we append a new row, _build_features will shift automatically.
                    # So let's just append a dummy row, run _build_features, and predict for that dummy row!
                    
                    dummy_row = pd.DataFrame([{
                        'sale_date': fd,
                        'quantity_sold': 0.0, # Target to predict
                        'selling_price': float(product.selling_price),
                        'discount': 0.0,
                        'revenue': 0.0
                    }])
                    
                    concat_df = pd.concat([temp_df, dummy_row], ignore_index=True)
                    concat_feat = _build_features(concat_df)
                    target_features = concat_feat.iloc[-1]
                    
                    # Construct exact X vector
                    X_pred_dict = {}
                    for c in feature_cols:
                        if c in row:
                            X_pred_dict[c] = row[c]
                        elif c in target_features:
                            X_pred_dict[c] = float(target_features[c])
                        else:
                            X_pred_dict[c] = 0.0
                            
                    X_pred = pd.DataFrame([X_pred_dict])
                    
                    pred_val = max(0.0, float(ml_model.predict(X_pred)[0]))
                    
                    if current_date == forecast_date:
                        predicted = pred_val
                        break
                        
                    # Add prediction to temp_df for next iteration
                    new_hist_row = pd.DataFrame([{
                        'sale_date': fd,
                        'quantity_sold': pred_val,
                        'selling_price': float(product.selling_price),
                        'discount': 0.0,
                        'revenue': pred_val * float(product.selling_price)
                    }])
                    temp_df = pd.concat([temp_df, new_hist_row], ignore_index=True)
                    current_date += timedelta(days=1)

            except Exception as e:
                predicted  = _moving_average_forecast(df)
                model_used = 'BaselineMovingAverage'
    else:
        # Baseline fallback
        if df.empty:
            return {
                'success': False,
                'message': (f'No sales history found for {product.product_name} in {store.store_name}. '
                            f'Record some sales first, then train the model.')
            }
        predicted = _moving_average_forecast(df)
        model_used = 'BaselineMovingAverage'

    predicted = round(predicted, 2)

    forecast_record = None
    if save:
        forecast_record = DemandForecast(
            product_id=product_id,
            store_id=store_id,
            forecast_date=forecast_date,
            predicted_demand=Decimal(str(predicted)),
            confidence_score=Decimal(str(round(quality_score, 2))),
            model_name=model_used,
            created_at=datetime.utcnow()
        )
        db.session.add(forecast_record)
        db.session.commit()

    historical = []
    if not df.empty:
        hist_df = df.tail(30)
        historical = [
            {'date': str(r['sale_date'].date()), 'quantity': int(r['quantity_sold'])}
            for _, r in hist_df.iterrows()
        ]

    return {
        'success': True,
        'product_name':     product.product_name,
        'store_name':       store.store_name,
        'forecast_date':    forecast_date_str,
        'predicted_demand': predicted,
        'model_name':       model_used,
        'quality_score':    quality_score,
        'quality_label':    'Model Quality Score (max(0, R²) × 100)' if model_used != 'BaselineMovingAverage' else 'Baseline (moving average — insufficient data/no ML model trained)',
        'historical_data':  historical,
        'forecast_id':      forecast_record.forecast_id if forecast_record else None,
        'metrics':          model_metadata.get('metrics') if model_metadata else None,
        'comparison':       model_metadata.get('comparison') if model_metadata else None
    }

