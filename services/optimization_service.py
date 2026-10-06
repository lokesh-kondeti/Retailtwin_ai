"""
Inventory Optimization Service.
Uses demand forecasts + inventory constraints to recommend reorder quantities.
Uses a simple, explainable EOQ-inspired strategy.
"""

from models import db
from models.inventory import Inventory
from models.demand_forecast import DemandForecast
from models.product import Product
from models.store import Store
from models.sales import Sales
from sqlalchemy import func


def generate_recommendation(product_id: int, store_id: int) -> dict:
    """
    Generate inventory optimization recommendation for a product/store.

    Strategy (simple and explainable):
    1. Get latest demand forecast (or use historical average).
    2. Calculate expected demand over lead_time days.
    3. Recommended stock = lead_time_demand + safety_stock.
    4. Safety stock = 1.5 × std_dev of daily demand.
    5. Reorder quantity = recommended_stock - current_stock.
    6. Status = LOW_STOCK / OK / OVERSTOCK.
    """
    product   = Product.query.get(product_id)
    store     = Store.query.get(store_id)
    inventory = Inventory.query.filter_by(product_id=product_id, store_id=store_id).first()

    if not product:
        return {'success': False, 'message': 'Product not found.'}
    if not store:
        return {'success': False, 'message': 'Store not found.'}
    if not inventory:
        return {'success': False, 'message': 'No inventory record found. Add inventory first.'}

    # Get latest forecast
    forecast = DemandForecast.query.filter_by(
        product_id=product_id, store_id=store_id
    ).order_by(DemandForecast.created_at.desc()).first()

    if forecast:
        daily_demand = float(forecast.predicted_demand)
        demand_source = f'ML Forecast ({forecast.model_name})'
    else:
        # Fallback: average daily sales
        avg = db.session.query(
            func.avg(Sales.quantity_sold)
        ).filter_by(product_id=product_id, store_id=store_id).scalar()
        daily_demand = float(avg or 0)
        demand_source = 'Historical Average'

    if daily_demand <= 0:
        return {
            'success': False,
            'message': 'No demand data available. Record sales or generate a forecast first.'
        }

    # Calculate demand standard deviation for safety stock
    sales_data = db.session.query(
        Sales.quantity_sold
    ).filter_by(product_id=product_id, store_id=store_id).all()

    quantities = [float(s[0]) for s in sales_data]
    if len(quantities) >= 3:
        import numpy as np
        std_demand = float(np.std(quantities))
    else:
        std_demand = daily_demand * 0.2  # Assume 20% variance if no history

    lead_time     = product.lead_time or 1
    safety_stock  = round(1.5 * std_demand * (lead_time ** 0.5), 0)
    lead_demand   = round(daily_demand * lead_time, 0)
    reorder_qty   = max(0, int(lead_demand + safety_stock - inventory.current_stock))
    recommended_stock = int(lead_demand + safety_stock)

    # Stockout risk
    days_of_stock = inventory.current_stock / daily_demand if daily_demand > 0 else 999
    if days_of_stock < lead_time:
        stockout_risk = 'HIGH'
        risk_message  = f'Current stock will last ~{days_of_stock:.1f} days but lead time is {lead_time} days. Reorder immediately.'
    elif days_of_stock < lead_time * 1.5:
        stockout_risk = 'MEDIUM'
        risk_message  = f'Stock may run low during replenishment window. Consider reordering soon.'
    else:
        stockout_risk = 'LOW'
        risk_message  = f'Current stock sufficient for approximately {days_of_stock:.1f} days.'

    # Overstock risk
    if inventory.current_stock > inventory.maximum_stock * 0.85:
        overstock_warning = True
        overstock_message = f'Stock ({inventory.current_stock}) is near maximum capacity ({inventory.maximum_stock}).'
    else:
        overstock_warning = False
        overstock_message = None

    return {
        'success': True,
        'product_name':    product.product_name,
        'store_name':      store.store_name,
        'current_stock':   inventory.current_stock,
        'reorder_level':   inventory.reorder_level,
        'daily_demand':    round(daily_demand, 2),
        'demand_source':   demand_source,
        'lead_time_days':  lead_time,
        'safety_stock':    int(safety_stock),
        'recommended_stock': recommended_stock,
        'reorder_quantity': reorder_qty,
        'reorder_status':  'REORDER_NOW' if reorder_qty > 0 and stockout_risk == 'HIGH' else ('REORDER_SOON' if reorder_qty > 0 else 'SUFFICIENT'),
        'stockout_risk':   stockout_risk,
        'risk_message':    risk_message,
        'overstock_warning': overstock_warning,
        'overstock_message': overstock_message,
        'methodology': (
            'Recommended Stock = (Daily Demand × Lead Time) + Safety Stock. '
            'Safety Stock = 1.5 × σ(demand) × √(lead_time). '
            'Reorder Qty = max(0, Recommended Stock − Current Stock).'
        )
    }
