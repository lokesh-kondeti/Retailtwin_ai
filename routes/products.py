"""Product CRUD routes."""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models import db
from models.product import Product
from models.category import Category
from models.demand_forecast import DemandForecast
from models.pricing_strategy import PricingStrategy
from utils.decorators import login_required, admin_required, get_current_user
from utils.validators import validate_required_string, validate_positive_number, validate_non_negative_int

products_bp = Blueprint('products', __name__)


@products_bp.route('/products')
@login_required
def index():
    current_user = get_current_user()
    categories = Category.query.order_by(Category.category_name).all()
    return render_template('products/index.html', current_user=current_user, categories=categories)


@products_bp.route('/api/products', methods=['GET'])
@login_required
def api_list():
    search      = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', type=int)

    query = Product.query
    if search:
        query = query.filter(Product.product_name.ilike(f'%{search}%'))
    if category_id:
        query = query.filter_by(category_id=category_id)

    products = query.order_by(Product.product_name).all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in products]})


@products_bp.route('/api/products', methods=['POST'])
@login_required
def api_create():
    data = request.get_json(silent=True) or {}

    name        = str(data.get('product_name', '')).strip()
    category_id = data.get('category_id')
    cost_price    = data.get('cost_price')
    selling_price = data.get('selling_price')
    lead_time   = data.get('lead_time', 1)
    expiry_days = data.get('expiry_days', 365)

    errors = []
    if not validate_required_string(name, 100):
        errors.append('Product name is required (max 100 chars).')
    if not category_id:
        errors.append('Category is required.')
    if not validate_positive_number(cost_price):
        errors.append('Cost price must be a positive number.')
    if not validate_positive_number(selling_price):
        errors.append('Selling price must be a positive number.')
    elif validate_positive_number(cost_price) and float(selling_price) < float(cost_price):
        errors.append('Selling price must be greater than or equal to cost price.')
    if not validate_non_negative_int(lead_time):
        errors.append('Lead time cannot be negative.')
    if not validate_non_negative_int(expiry_days):
        errors.append('Expiry days cannot be negative.')

    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    # Check category exists
    if not Category.query.get(category_id):
        return jsonify({'success': False, 'message': 'Category not found'}), 404

    product = Product(
        product_name=name,
        category_id=int(category_id),
        cost_price=float(cost_price),
        selling_price=float(selling_price),
        lead_time=int(lead_time),
        expiry_days=int(expiry_days)
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Product created', 'data': product.to_dict()}), 201


@products_bp.route('/api/products/<int:product_id>', methods=['GET'])
@login_required
def api_get(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({'success': True, 'data': product.to_dict()})


@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def api_update(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json(silent=True) or {}

    name        = str(data.get('product_name', product.product_name)).strip()
    category_id = data.get('category_id', product.category_id)
    cost_price    = data.get('cost_price', product.cost_price)
    selling_price = data.get('selling_price', product.selling_price)
    lead_time   = data.get('lead_time', product.lead_time)
    expiry_days = data.get('expiry_days', product.expiry_days)

    errors = []
    if not validate_required_string(name, 100):
        errors.append('Product name is required.')
    if not validate_positive_number(cost_price):
        errors.append('Cost price must be positive.')
    if not validate_positive_number(selling_price):
        errors.append('Selling price must be positive.')
    elif validate_positive_number(cost_price) and float(selling_price) < float(cost_price):
        errors.append('Selling price must be greater than or equal to cost price.')
    if not validate_non_negative_int(lead_time):
        errors.append('Lead time cannot be negative.')
    if not validate_non_negative_int(expiry_days):
        errors.append('Expiry days cannot be negative.')
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    if not Category.query.get(category_id):
        return jsonify({'success': False, 'message': 'Category not found'}), 404

    product.product_name = name
    product.category_id  = int(category_id)
    product.cost_price   = float(cost_price)
    product.selling_price = float(selling_price)
    product.lead_time    = int(lead_time)
    product.expiry_days  = int(expiry_days)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Product updated', 'data': product.to_dict()})


@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def api_delete(product_id):
    product = Product.query.get_or_404(product_id)
    
    # 8. Explicitly check for RESTRICT dependencies to avoid losing important data
    if product.sales.count() > 0:
        return jsonify({'success': False, 'message': 'Cannot delete product: Historical sales records exist.'}), 409
    if product.inventory_items.count() > 0:
        return jsonify({'success': False, 'message': 'Cannot delete product: Inventory records exist.'}), 409
    if product.simulations.count() > 0:
        return jsonify({'success': False, 'message': 'Cannot delete product: Digital Twin simulation records exist.'}), 409

    try:
        # 9. Delete generated ML dependencies (DemandForecast, PricingStrategy)
        DemandForecast.query.filter_by(product_id=product_id).delete()
        PricingStrategy.query.filter_by(product_id=product_id).delete()
        
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Cannot delete: {str(e)}'}), 409
