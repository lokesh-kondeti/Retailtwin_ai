"""Inventory optimization routes."""

from flask import Blueprint, render_template, request, jsonify
from models.product import Product
from models.store import Store
from utils.decorators import login_required, get_current_user

optimization_bp = Blueprint('optimization', __name__)


@optimization_bp.route('/optimization')
@login_required
def index():
    current_user = get_current_user()
    stores   = Store.query.order_by(Store.store_name).all()
    products = Product.query.order_by(Product.product_name).all()
    return render_template('optimization/index.html', current_user=current_user,
                           stores=stores, products=products)


@optimization_bp.route('/api/optimization', methods=['POST'])
@login_required
def api_optimize():
    """Generate inventory optimization recommendation."""
    from services.optimization_service import generate_recommendation
    data = request.get_json(silent=True) or {}

    product_id = data.get('product_id')
    store_id   = data.get('store_id')

    if not product_id or not store_id:
        return jsonify({'success': False, 'message': 'product_id and store_id are required.'}), 400

    result = generate_recommendation(int(product_id), int(store_id))
    if result.get('success'):
        return jsonify(result)
    return jsonify(result), 400
