"""Inventory management routes."""

from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
from models import db
from models.inventory import Inventory
from models.product import Product
from models.store import Store
from utils.decorators import login_required, get_current_user
from utils.validators import validate_non_negative_int

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/inventory')
@login_required
def index():
    current_user = get_current_user()
    stores   = Store.query.order_by(Store.store_name).all()
    products = Product.query.order_by(Product.product_name).all()
    return render_template('inventory/index.html', current_user=current_user,
                           stores=stores, products=products)


@inventory_bp.route('/api/inventory', methods=['GET'])
@login_required
def api_list():
    store_id   = request.args.get('store_id', type=int)
    product_id = request.args.get('product_id', type=int)
    status     = request.args.get('status', '').strip().upper()

    query = Inventory.query
    if store_id:
        query = query.filter_by(store_id=store_id)
    if product_id:
        query = query.filter_by(product_id=product_id)

    items = query.all()

    if status:
        items = [i for i in items if i.stock_status == status]

    return jsonify({'success': True, 'data': [i.to_dict() for i in items]})


@inventory_bp.route('/api/inventory', methods=['POST'])
@login_required
def api_create():
    data = request.get_json(silent=True) or {}
    product_id    = data.get('product_id')
    store_id      = data.get('store_id')
    current_stock = data.get('current_stock', 0)
    minimum_stock = data.get('minimum_stock', 0)
    maximum_stock = data.get('maximum_stock', 1000)
    reorder_level = data.get('reorder_level', 10)

    errors = []
    if not product_id: errors.append('Product is required.')
    if not store_id:   errors.append('Store is required.')
    if not validate_non_negative_int(current_stock): errors.append('Current stock cannot be negative.')
    if not validate_non_negative_int(minimum_stock): errors.append('Minimum stock cannot be negative.')
    if not validate_non_negative_int(maximum_stock): errors.append('Maximum stock cannot be negative.')
    if not validate_non_negative_int(reorder_level): errors.append('Reorder level cannot be negative.')
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    if not Product.query.get(product_id):
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    if not Store.query.get(store_id):
        return jsonify({'success': False, 'message': 'Store not found'}), 404

    existing = Inventory.query.filter_by(product_id=product_id, store_id=store_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'Inventory record already exists for this product/store.'}), 409

    inv = Inventory(
        product_id=int(product_id), store_id=int(store_id),
        current_stock=int(current_stock), minimum_stock=int(minimum_stock),
        maximum_stock=int(maximum_stock), reorder_level=int(reorder_level),
        last_updated=datetime.utcnow()
    )
    db.session.add(inv)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Inventory record created', 'data': inv.to_dict()}), 201


@inventory_bp.route('/api/inventory/<int:inventory_id>', methods=['GET'])
@login_required
def api_get(inventory_id):
    inv = Inventory.query.get_or_404(inventory_id)
    return jsonify({'success': True, 'data': inv.to_dict()})


@inventory_bp.route('/api/inventory/<int:inventory_id>', methods=['PUT'])
@login_required
def api_update(inventory_id):
    inv  = Inventory.query.get_or_404(inventory_id)
    data = request.get_json(silent=True) or {}

    errors = []
    if 'current_stock' in data and not validate_non_negative_int(data['current_stock']):
        errors.append('Current stock cannot be negative.')
    if 'minimum_stock' in data and not validate_non_negative_int(data['minimum_stock']):
        errors.append('Minimum stock cannot be negative.')
    if 'maximum_stock' in data and not validate_non_negative_int(data['maximum_stock']):
        errors.append('Maximum stock cannot be negative.')
    if 'reorder_level' in data and not validate_non_negative_int(data['reorder_level']):
        errors.append('Reorder level cannot be negative.')
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    if 'current_stock' in data: inv.current_stock = int(data['current_stock'])
    if 'minimum_stock' in data: inv.minimum_stock = int(data['minimum_stock'])
    if 'maximum_stock' in data: inv.maximum_stock = int(data['maximum_stock'])
    if 'reorder_level' in data: inv.reorder_level = int(data['reorder_level'])
    inv.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Inventory updated', 'data': inv.to_dict()})
