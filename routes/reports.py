"""Reports routes with filtering and CSV export."""

import csv
import io
from flask import Blueprint, render_template, request, jsonify, Response
from sqlalchemy import func
from datetime import date

from models import db
from models.sales import Sales
from models.inventory import Inventory
from models.demand_forecast import DemandForecast
from models.digital_twin import DigitalTwinSimulation
from models.product import Product
from models.store import Store
from utils.decorators import login_required, get_current_user

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def index():
    current_user = get_current_user()
    stores   = Store.query.order_by(Store.store_name).all()
    products = Product.query.order_by(Product.product_name).all()
    return render_template('reports/index.html', current_user=current_user,
                           stores=stores, products=products)


@reports_bp.route('/api/reports/sales', methods=['GET'])
@login_required
def api_sales_report():
    store_id   = request.args.get('store_id', type=int)
    product_id = request.args.get('product_id', type=int)
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')
    export     = request.args.get('export', '').lower() == 'csv'

    query = Sales.query
    if store_id:   query = query.filter_by(store_id=store_id)
    if product_id: query = query.filter_by(product_id=product_id)
    if date_from:
        try: query = query.filter(Sales.sale_date >= date.fromisoformat(date_from))
        except ValueError: pass
    if date_to:
        try: query = query.filter(Sales.sale_date <= date.fromisoformat(date_to))
        except ValueError: pass

    sales = query.order_by(Sales.sale_date.desc()).all()

    if export:
        return _export_sales_csv(sales)

    total_revenue  = sum(float(s.revenue) for s in sales)
    total_quantity = sum(s.quantity_sold for s in sales)
    return jsonify({
        'success': True,
        'summary': {'total_records': len(sales), 'total_revenue': total_revenue,
                    'total_quantity': total_quantity},
        'data': [s.to_dict() for s in sales]
    })


def _export_sales_csv(sales):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Sale ID', 'Product', 'Store', 'Date', 'Quantity', 'Cost Price', 'Selling Price', 'Discount', 'Revenue', 'Profit'])
    for s in sales:
        cost = float(s.cost_price)
        revenue = float(s.revenue)
        profit = revenue - (s.quantity_sold * cost)
        writer.writerow([
            s.sale_id,
            s.product.product_name if s.product else s.product_id,
            s.store.store_name if s.store else s.store_id,
            s.sale_date, s.quantity_sold, cost,
            float(s.selling_price), float(s.discount), revenue, round(profit, 2)
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sales_report.csv'}
    )


@reports_bp.route('/api/reports/inventory', methods=['GET'])
@login_required
def api_inventory_report():
    store_id = request.args.get('store_id', type=int)
    export   = request.args.get('export', '').lower() == 'csv'

    query = Inventory.query
    if store_id: query = query.filter_by(store_id=store_id)
    items = query.all()

    data = [i.to_dict() for i in items]
    if export:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Product', 'Store', 'Current Stock', 'Min', 'Max', 'Reorder', 'Status'])
        for d in data:
            writer.writerow([d['inventory_id'], d['product_name'], d['store_name'],
                             d['current_stock'], d['minimum_stock'], d['maximum_stock'],
                             d['reorder_level'], d['stock_status']])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=inventory_report.csv'})

    return jsonify({'success': True, 'data': data})


@reports_bp.route('/api/reports/optimization', methods=['GET'])
@login_required
def api_optimization_report():
    """Generate optimization recommendations for all inventory records."""
    from services.optimization_service import generate_recommendation
    store_id   = request.args.get('store_id', type=int)
    product_id = request.args.get('product_id', type=int)
    export     = request.args.get('export', '').lower() == 'csv'

    query = Inventory.query
    if store_id:   query = query.filter_by(store_id=store_id)
    if product_id: query = query.filter_by(product_id=product_id)
    items = query.all()

    results = []
    for inv in items:
        rec = generate_recommendation(inv.product_id, inv.store_id)
        if rec.get('success'):
            results.append(rec)

    if export:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Store', 'Current Stock', 'Daily Demand', 'Lead Time',
                         'Safety Stock', 'Recommended Stock', 'Reorder Qty', 'Stockout Risk', 'Status'])
        for r in results:
            writer.writerow([r['product_name'], r['store_name'], r['current_stock'],
                             r['daily_demand'], r['lead_time_days'], r['safety_stock'],
                             r['recommended_stock'], r['reorder_quantity'],
                             r['stockout_risk'], r['reorder_status']])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=optimization_report.csv'})

    return jsonify({'success': True, 'data': results})


@reports_bp.route('/api/reports/forecasts', methods=['GET'])
@login_required
def api_forecast_report():
    product_id = request.args.get('product_id', type=int)
    store_id   = request.args.get('store_id', type=int)
    export     = request.args.get('export', '').lower() == 'csv'
    query = DemandForecast.query
    if product_id: query = query.filter_by(product_id=product_id)
    if store_id:   query = query.filter_by(store_id=store_id)
    forecasts = query.order_by(DemandForecast.forecast_date.desc()).limit(100).all()

    if export:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Store', 'Forecast Date', 'Predicted Demand', 'Model', 'Quality Score'])
        for f in forecasts:
            writer.writerow([f.product.product_name if f.product else f.product_id,
                             f.store.store_name if f.store else f.store_id,
                             f.forecast_date, float(f.predicted_demand),
                             f.model_name, float(f.confidence_score)])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=forecast_report.csv'})

    return jsonify({'success': True, 'data': [f.to_dict() for f in forecasts]})


@reports_bp.route('/api/reports/simulations', methods=['GET'])
@login_required
def api_simulation_report():
    store_id   = request.args.get('store_id', type=int)
    product_id = request.args.get('product_id', type=int)
    export     = request.args.get('export', '').lower() == 'csv'
    query = DigitalTwinSimulation.query
    if store_id:   query = query.filter_by(store_id=store_id)
    if product_id: query = query.filter_by(product_id=product_id)
    sims = query.order_by(DigitalTwinSimulation.simulation_date.desc()).limit(100).all()

    if export:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Scenario', 'Product', 'Store', 'Stock', 'Sales', 'Revenue', 'Profit',
                         'Stockout', 'Overstock', 'Loss', 'Date', 'Recommendation'])
        for s in sims:
            writer.writerow([s.scenario_name,
                             s.product.product_name if s.product else s.product_id,
                             s.store.store_name if s.store else s.store_id,
                             s.simulated_stock, float(s.expected_sales), float(s.expected_revenue),
                             float(s.expected_profit), s.expected_stockout, s.expected_overstock,
                             float(s.expected_loss), s.simulation_date, s.recommendation])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                        headers={'Content-Disposition': 'attachment; filename=simulation_report.csv'})

    return jsonify({'success': True, 'data': [s.to_dict() for s in sims]})
