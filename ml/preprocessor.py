"""
ML Preprocessor — builds the training dataset from the sales database.

Used by the training script and the forecast service.
Applies feature engineering without data leakage.
"""

import sys
import os

# Allow running directly as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime


def build_global_training_set() -> pd.DataFrame:
    """
    Load all sales from the database and build a feature-engineered DataFrame.
    Must be called from within a Flask application context.

    Returns None if no data is available.
    """
    from models.sales import Sales
    from models.product import Product

    sales = Sales.query.order_by(Sales.sale_date, Sales.product_id, Sales.store_id).all()
    if not sales:
        return None

    rows = []
    for s in sales:
        rows.append({
            'sale_id':      s.sale_id,
            'product_id':   s.product_id,
            'store_id':     s.store_id,
            'sale_date':    s.sale_date,
            'quantity_sold': s.quantity_sold,
            'selling_price': float(s.selling_price),
            'discount':     float(s.discount),
            'revenue':      float(s.revenue),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['sale_date'] = pd.to_datetime(df['sale_date'])

    # Sort chronologically — critical for lag features without data leakage
    df = df.sort_values(['product_id', 'store_id', 'sale_date']).reset_index(drop=True)

    # Time-based features
    df['day_of_week']  = df['sale_date'].dt.dayofweek
    df['day_of_month'] = df['sale_date'].dt.day
    df['month']        = df['sale_date'].dt.month
    df['quarter']      = df['sale_date'].dt.quarter
    df['is_weekend']   = (df['day_of_week'] >= 5).astype(int)
    df['week_of_year'] = df['sale_date'].dt.isocalendar().week.astype(int)

    # Lag features per product+store group (no leakage — shift applied within group)
    grouped = df.groupby(['product_id', 'store_id'])['quantity_sold']
    
    df['lag_1']  = grouped.shift(1)
    df['lag_2']  = grouped.shift(2)
    df['lag_3']  = grouped.shift(3)
    df['lag_7']  = grouped.shift(7)
    df['lag_14'] = grouped.shift(14)
    df['lag_21'] = grouped.shift(21)
    df['lag_28'] = grouped.shift(28)

    # Rolling stats (shift(1) prevents looking at current row)
    df['rolling_mean_3'] = grouped.transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    df['rolling_mean_7'] = grouped.transform(lambda x: x.shift(1).rolling(7, min_periods=1).mean())
    df['rolling_mean_14'] = grouped.transform(lambda x: x.shift(1).rolling(14, min_periods=1).mean())
    df['rolling_mean_28'] = grouped.transform(lambda x: x.shift(1).rolling(28, min_periods=1).mean())
    
    df['rolling_std_7'] = grouped.transform(lambda x: x.shift(1).rolling(7, min_periods=1).std())
    df['rolling_std_14'] = grouped.transform(lambda x: x.shift(1).rolling(14, min_periods=1).std())
    df['rolling_std_28'] = grouped.transform(lambda x: x.shift(1).rolling(28, min_periods=1).std())

    # Fill NaNs with 0 to allow training on smaller datasets while keeping standard dimensions
    df = df.fillna(0).reset_index(drop=True)

    return df


if __name__ == '__main__':
    # Quick test: run from project root with Flask context
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, '.env'))

    from app import create_app
    app = create_app()
    with app.app_context():
        df = build_global_training_set()
        if df is not None and not df.empty:
            print(f"Training set built: {len(df)} rows, {df.shape[1]} columns")
            print(df.dtypes)
            print(df.head())
        else:
            print("No data available.")
