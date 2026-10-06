# Architecture & Technical Stack

## Stack Overview
- **Backend**: Python 3.11, Flask (Application Factory Pattern)
- **Database**: MySQL 8.x, SQLAlchemy ORM
- **Frontend**: HTML5, Bootstrap 5.3, Vanilla JS, Chart.js
- **Machine Learning**: Scikit-Learn (RandomForestRegressor), Pandas

## Directory Structure
- \models/\: SQLAlchemy database models (10 core tables).
- \outes/\: Flask Blueprints for API and template rendering.
- \services/\: Core business logic (Forecast, Simulation, Optimization).
- \ml/\: Data preprocessing and standalone training scripts.
- \	emplates/\: Jinja2 HTML templates.
- \static/\: CSS/JS assets.

## Core Modules

### 1. ML Demand Forecasting
- Extracts historical sales data.
- Generates lag and rolling window features (e.g., lag_7, rolling_mean_14) without data leakage.
- Trains a \RandomForestRegressor\ to predict future demand.
- Falls back to a Simple Moving Average if insufficient data (<30 records).

### 2. Digital Twin Simulation
- Virtual environment to run hypothetical inventory scenarios.
- Calculates projected Sales, Revenue, Profit, Stockout (opportunity loss), and Overstock based on predicted demand.
- Scores scenarios: \profit - (overstock × cost_price × 0.1) - (stockout × selling_price × 0.3)\.

### 3. Inventory Optimization
- Uses an EOQ-inspired logic tailored for retail.
- Computes Lead Time Demand and Safety Stock (z-score = 1.645 for 95% service level).
- Recommends Reorder Quantity based on current stock, minimum stock, and maximum stock levels.
