"""Sales recording routes with atomic inventory update."""

from flask import Blueprint, render_template, request, jsonify
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models.sales import Sales
from models.inventory import Inventory
from models.product import Product
from models.store import Store
from utils.decorators import login_required, get_current_user
from utils.validators import validate_positive_number, validate_non_negative_int

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/sales')
@login_required
def index():
    current_user = get_current_user()
    stores   = Store.query.order_by(Store.store_name).all()
    products = Product.query.order_by(Product.product_name).all()
    return render_template('sales/index.html', current_user=current_user,
                           stores=stores, products=products)


@sales_bp.route('/api/sales', methods=['GET'])
@login_required
def api_list():
    store_id   = request.args.get('store_id', type=int)
    product_id = request.args.get('product_id', type=int)
    date_from  = request.args.get('date_from', '')
    date_to    = request.args.get('date_to', '')
    limit      = request.args.get('limit', 100, type=int)

    query = Sales.query
    if store_id:   query = query.filter_by(store_id=store_id)
    if product_id: query = query.filter_by(product_id=product_id)
    if date_from:
        try:
            query = query.filter(Sales.sale_date >= date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Sales.sale_date <= date.fromisoformat(date_to))
        except ValueError:
            pass

    sales = query.order_by(Sales.sale_date.desc(), Sales.created_at.desc()).limit(limit).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in sales]})


@sales_bp.route('/api/sales', methods=['POST'])
@login_required
def api_create():
    """Record a sale and atomically reduce inventory.

    selling_price and cost_price are always fetched from the Product record —
    the client must NOT supply or override them.
    """
    data = request.get_json(silent=True) or {}

    product_id    = data.get('product_id')
    store_id      = data.get('store_id')
    sale_date_str = data.get('sale_date', str(date.today()))
    quantity      = data.get('quantity_sold')
    discount      = data.get('discount', 0)

    # Validation — selling_price is NOT accepted from the client
    errors = []
    if not product_id:                              errors.append('Product is required.')
    if not store_id:                                errors.append('Store is required.')
    if not validate_positive_number(quantity, False): errors.append('Quantity must be a positive integer.')
    if not validate_non_negative_int(discount) and not validate_positive_number(discount, True):
        errors.append('Discount must be >= 0.')
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    quantity = int(quantity)
    discount = Decimal(str(discount))

    try:
        sale_date = date.fromisoformat(sale_date_str)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid sale date format (YYYY-MM-DD).'}), 400

    # Verify product and store exist
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'success': False, 'message': 'Product not found.'}), 404
    if not Store.query.get(store_id):
        return jsonify({'success': False, 'message': 'Store not found.'}), 404

    # Authoritative prices come from the Product record, not from the client
    price      = Decimal(str(product.selling_price))
    cost_price = Decimal(str(product.cost_price))

    # Check inventory
    inventory = Inventory.query.filter_by(
        product_id=int(product_id), store_id=int(store_id)
    ).with_for_update().first()

    if not inventory:
        return jsonify({'success': False,
                        'message': 'No inventory record found for this product/store.'}), 404

    if inventory.current_stock < quantity:
        return jsonify({
            'success': False,
            'message': f'Insufficient stock. Available: {inventory.current_stock}, Requested: {quantity}.'
        }), 409

    # Atomic update inside try/except with rollback
    try:
        revenue = Sales.calculate_revenue(quantity, price, discount)

        sale = Sales(
            product_id=int(product_id),
            store_id=int(store_id),
            sale_date=sale_date,
            quantity_sold=quantity,
            cost_price=cost_price,
            selling_price=price,
            discount=discount,
            revenue=revenue,
            created_at=datetime.utcnow()
        )
        db.session.add(sale)

        # Reduce inventory
        inventory.current_stock -= quantity
        inventory.last_updated   = datetime.utcnow()

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Sale recorded and inventory updated.',
            'data': sale.to_dict()
        }), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Database error: {str(e)}'}), 500

