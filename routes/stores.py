"""Store CRUD routes."""

from flask import Blueprint, render_template, request, jsonify
from models import db
from models.store import Store
from utils.decorators import login_required, admin_required, get_current_user
from utils.validators import validate_required_string

stores_bp = Blueprint('stores', __name__)


@stores_bp.route('/stores')
@login_required
def index():
    current_user = get_current_user()
    return render_template('stores/index.html', current_user=current_user)


@stores_bp.route('/api/stores', methods=['GET'])
@login_required
def api_list():
    search = request.args.get('search', '').strip()
    query  = Store.query
    if search:
        query = query.filter(Store.store_name.ilike(f'%{search}%'))
    stores = query.order_by(Store.store_name).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in stores]})


@stores_bp.route('/api/stores', methods=['POST'])
@login_required
def api_create():
    data = request.get_json(silent=True) or {}
    name     = str(data.get('store_name', '')).strip()
    location = str(data.get('location', '')).strip()
    manager  = str(data.get('manager_name', '')).strip()
    contact  = str(data.get('contact', '')).strip()

    if not validate_required_string(name, 100):
        return jsonify({'success': False, 'message': 'Store name is required.'}), 400

    if Store.query.filter(Store.store_name.ilike(name)).first():
        return jsonify({'success': False, 'message': f'A store named "{name}" already exists.'}), 409

    store = Store(store_name=name, location=location or None,
                  manager_name=manager or None, contact=contact or None)
    db.session.add(store)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Store created', 'data': store.to_dict()}), 201


@stores_bp.route('/api/stores/<int:store_id>', methods=['GET'])
@login_required
def api_get(store_id):
    store = Store.query.get_or_404(store_id)
    return jsonify({'success': True, 'data': store.to_dict()})


@stores_bp.route('/api/stores/<int:store_id>', methods=['PUT'])
@login_required
def api_update(store_id):
    store = Store.query.get_or_404(store_id)
    data  = request.get_json(silent=True) or {}
    name  = str(data.get('store_name', store.store_name)).strip()

    if not validate_required_string(name, 100):
        return jsonify({'success': False, 'message': 'Store name is required.'}), 400

    # Guard against renaming to an existing store name (exclude self)
    conflict = Store.query.filter(Store.store_name.ilike(name), Store.store_id != store_id).first()
    if conflict:
        return jsonify({'success': False, 'message': f'A store named "{name}" already exists.'}), 409

    store.store_name   = name
    store.location     = str(data.get('location', store.location or '')).strip() or None
    store.manager_name = str(data.get('manager_name', store.manager_name or '')).strip() or None
    store.contact      = str(data.get('contact', store.contact or '')).strip() or None
    db.session.commit()
    return jsonify({'success': True, 'message': 'Store updated', 'data': store.to_dict()})


@stores_bp.route('/api/stores/<int:store_id>', methods=['DELETE'])
@admin_required
def api_delete(store_id):
    store = Store.query.get_or_404(store_id)

    # --- RESTRICT: Protect important historical/business records ---
    if store.sales.count() > 0:
        return jsonify({
            'success': False,
            'message': (
                f'Cannot delete "{store.store_name}": it has historical sales records. '
                'Archive or reassign the store instead.'
            )
        }), 409

    if store.inventory_items.count() > 0:
        return jsonify({
            'success': False,
            'message': (
                f'Cannot delete "{store.store_name}": it has inventory records. '
                'Clear the inventory before deleting.'
            )
        }), 409

    if store.simulations.count() > 0:
        return jsonify({
            'success': False,
            'message': (
                f'Cannot delete "{store.store_name}": it has Digital Twin simulation records.'
            )
        }), 409

    if store.customer_flows.count() > 0:
        return jsonify({
            'success': False,
            'message': (
                f'Cannot delete "{store.store_name}": it has customer flow records.'
            )
        }), 409

    try:
        # Safe to remove: ML-generated forecast records have no independent business value
        from models.demand_forecast import DemandForecast
        DemandForecast.query.filter_by(store_id=store_id).delete()

        db.session.delete(store)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Store "{store.store_name}" deleted.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Cannot delete store: {str(e)}'}), 409
