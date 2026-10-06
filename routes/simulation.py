"""Digital Twin simulation routes."""

from flask import Blueprint, render_template, request, jsonify
from models.product import Product
from models.store import Store
from models.digital_twin import DigitalTwinSimulation
from utils.decorators import login_required, get_current_user

simulation_bp = Blueprint('simulation', __name__)


@simulation_bp.route('/simulation')
@login_required
def index():
    current_user = get_current_user()
    stores   = Store.query.order_by(Store.store_name).all()
    products = Product.query.order_by(Product.product_name).all()
    return render_template('simulation/index.html', current_user=current_user,
                           stores=stores, products=products)


@simulation_bp.route('/api/simulation', methods=['POST'])
@login_required
def api_run():
    """Run a Digital Twin simulation scenario."""
    from services.simulation_service import run_simulation
    data = request.get_json(silent=True) or {}

    required = ['product_id', 'store_id', 'scenario_name', 'simulated_stock',
                'selling_price', 'cost_price', 'simulation_days']
    missing = [k for k in required if k not in data or data[k] == '']
    if missing:
        return jsonify({'success': False,
                        'message': f'Missing fields: {", ".join(missing)}'}), 400

    result = run_simulation(data)
    if result.get('success'):
        return jsonify(result), 201
    return jsonify(result), 400


@simulation_bp.route('/api/simulations', methods=['GET'])
@login_required
def api_list():
    product_id = request.args.get('product_id', type=int)
    store_id   = request.args.get('store_id', type=int)
    limit      = request.args.get('limit', 20, type=int)

    query = DigitalTwinSimulation.query
    if product_id: query = query.filter_by(product_id=product_id)
    if store_id:   query = query.filter_by(store_id=store_id)

    sims = query.order_by(DigitalTwinSimulation.simulation_date.desc()).limit(limit).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in sims]})


@simulation_bp.route('/api/simulations/compare', methods=['POST'])
@login_required
def api_compare():
    """Compare multiple simulation scenarios and return recommendation."""
    from services.simulation_service import compare_scenarios
    data = request.get_json(silent=True) or {}
    simulation_ids = data.get('simulation_ids', [])

    if not simulation_ids or len(simulation_ids) < 2:
        return jsonify({'success': False, 'message': 'Provide at least 2 simulation IDs.'}), 400

    result = compare_scenarios(simulation_ids)
    return jsonify(result)
