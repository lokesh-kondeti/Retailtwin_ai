"""Demand forecast routes."""

from flask import Blueprint, render_template, request, jsonify
from models import db
from models.demand_forecast import DemandForecast
from models.product import Product
from models.store import Store
from utils.decorators import login_required, get_current_user

forecast_bp = Blueprint('forecast', __name__)


@forecast_bp.route('/forecast')
@login_required
def index():
    current_user = get_current_user()
    stores   = Store.query.order_by(Store.store_name).all()
    products = Product.query.order_by(Product.product_name).all()
    return render_template('forecast/index.html', current_user=current_user,
                           stores=stores, products=products)


@forecast_bp.route('/api/forecast', methods=['POST'])
@login_required
def api_generate():
    """Generate demand forecast for a product/store/date."""
    from services.forecast_service import generate_forecast
    data = request.get_json(silent=True) or {}

    product_id    = data.get('product_id')
    store_id      = data.get('store_id')
    forecast_date = data.get('forecast_date')
    save          = data.get('save', True)

    if not product_id or not store_id or not forecast_date:
        return jsonify({'success': False,
                        'message': 'product_id, store_id, and forecast_date are required.'}), 400

    if not Product.query.get(product_id):
        return jsonify({'success': False, 'message': 'Product not found.'}), 404
    if not Store.query.get(store_id):
        return jsonify({'success': False, 'message': 'Store not found.'}), 404

    result = generate_forecast(int(product_id), int(store_id), forecast_date, save=save)
    if result.get('success'):
        return jsonify(result), 200
    return jsonify(result), 400


@forecast_bp.route('/api/forecasts', methods=['GET'])
@login_required
def api_list():
    product_id = request.args.get('product_id', type=int)
    store_id   = request.args.get('store_id', type=int)
    limit      = request.args.get('limit', 50, type=int)

    query = DemandForecast.query
    if product_id: query = query.filter_by(product_id=product_id)
    if store_id:   query = query.filter_by(store_id=store_id)

    forecasts = query.order_by(DemandForecast.created_at.desc()).limit(limit).all()
    return jsonify({'success': True, 'data': [f.to_dict() for f in forecasts]})


@forecast_bp.route('/api/forecasts/train', methods=['POST'])
@login_required
def api_train():
    """Trigger ML model training."""
    from services.forecast_service import train_model
    result = train_model()
    if result.get('success'):
        return jsonify(result), 200
    return jsonify(result), 400
