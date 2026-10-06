"""Dashboard route — main overview page."""

from flask import Blueprint, render_template, jsonify, session
from sqlalchemy import func, desc
from datetime import date, timedelta

from utils.decorators import login_required, get_current_user
from models import db
from models.product import Product
from models.store import Store
from models.inventory import Inventory
from models.sales import Sales
from models.demand_forecast import DemandForecast
from models.digital_twin import DigitalTwinSimulation

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required
def index():
    current_user = get_current_user()
    return render_template('dashboard/index.html', current_user=current_user)


@dashboard_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """Return all dashboard KPIs from the database."""
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    try:
        total_products = Product.query.count()
        total_stores   = Store.query.count()

        # Total current inventory units
        total_inventory = db.session.query(func.sum(Inventory.current_stock)).scalar() or 0

        # Low stock count
        low_stock_count = Inventory.query.filter(
            Inventory.current_stock <= Inventory.reorder_level
        ).count()

        # Today's sales
        todays_sales = db.session.query(
            func.count(Sales.sale_id),
            func.coalesce(func.sum(Sales.revenue), 0)
        ).filter(Sales.sale_date == today).one()

        todays_sale_count   = todays_sales[0]
        todays_revenue      = float(todays_sales[1])

        # Total revenue last 30 days
        total_revenue_30d = db.session.query(
            func.coalesce(func.sum(Sales.revenue), 0)
        ).filter(Sales.sale_date >= thirty_days_ago).scalar() or 0

        # Sales trend — last 14 days
        sales_trend = db.session.query(
            Sales.sale_date,
            func.sum(Sales.revenue).label('revenue'),
            func.sum(Sales.quantity_sold).label('units')
        ).filter(
            Sales.sale_date >= today - timedelta(days=14)
        ).group_by(Sales.sale_date).order_by(Sales.sale_date).all()

        sales_trend_data = [
            {'date': str(r.sale_date), 'revenue': float(r.revenue), 'units': int(r.units)}
            for r in sales_trend
        ]

        # Top 5 products by revenue last 30 days
        top_products = db.session.query(
            Product.product_name,
            func.sum(Sales.revenue).label('revenue'),
            func.sum(Sales.quantity_sold).label('units')
        ).join(Sales, Sales.product_id == Product.product_id).filter(
            Sales.sale_date >= thirty_days_ago
        ).group_by(Product.product_id, Product.product_name
        ).order_by(desc('revenue')).limit(5).all()

        top_products_data = [
            {'name': r.product_name, 'revenue': float(r.revenue), 'units': int(r.units)}
            for r in top_products
        ]

        # Inventory status distribution
        inventory_all = Inventory.query.all()
        inv_status = {'NORMAL': 0, 'LOW_STOCK': 0, 'OVERSTOCK': 0, 'OUT_OF_STOCK': 0}
        for inv in inventory_all:
            inv_status[inv.stock_status] = inv_status.get(inv.stock_status, 0) + 1

        # Latest forecasts
        latest_forecasts = DemandForecast.query.order_by(
            desc(DemandForecast.created_at)
        ).limit(5).all()
        forecasts_data = [f.to_dict() for f in latest_forecasts]

        # Recent simulations
        recent_simulations = DigitalTwinSimulation.query.order_by(
            desc(DigitalTwinSimulation.simulation_date)
        ).limit(5).all()
        simulations_data = [s.to_dict() for s in recent_simulations]

        return jsonify({
            'success': True,
            'data': {
                'total_products':    total_products,
                'total_stores':      total_stores,
                'total_inventory':   int(total_inventory),
                'low_stock_count':   low_stock_count,
                'todays_sales':      todays_sale_count,
                'todays_revenue':    todays_revenue,
                'total_revenue_30d': float(total_revenue_30d),
                'sales_trend':       sales_trend_data,
                'top_products':      top_products_data,
                'inventory_status':  inv_status,
                'latest_forecasts':  forecasts_data,
                'recent_simulations': simulations_data,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
