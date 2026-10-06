"""
RetailTwin AI — Application Entry Point
Run with: python app.py
"""

import os
from flask import Flask, redirect, url_for
from flask_cors import CORS

from config import get_config
from models import db

# Import all models so SQLAlchemy registers them before any db.create_all()
from models.user import User
from models.store import Store
from models.category import Category
from models.product import Product
from models.inventory import Inventory
from models.sales import Sales
from models.demand_forecast import DemandForecast
from models.pricing_strategy import PricingStrategy
from models.digital_twin import DigitalTwinSimulation
from models.customer_flow import CustomerFlow


def create_app(config_class=None):
    """Application factory — creates and configures the Flask app."""
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Enable CORS for API routes
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize SQLAlchemy
    db.init_app(app)

    # Register route blueprints
    _register_blueprints(app)

    # Root redirect to dashboard (or login)
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Centralized error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import request, jsonify, render_template
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Endpoint not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        from flask import request, jsonify, render_template
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        from flask import request, jsonify, render_template
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        return render_template('errors/403.html'), 403

    return app


def _register_blueprints(app: Flask):
    """Register all route blueprints with the application."""
    from routes.auth       import auth_bp
    from routes.dashboard  import dashboard_bp
    from routes.products   import products_bp
    from routes.categories import categories_bp
    from routes.stores     import stores_bp
    from routes.inventory  import inventory_bp
    from routes.sales      import sales_bp
    from routes.forecast   import forecast_bp
    from routes.simulation import simulation_bp
    from routes.optimization import optimization_bp
    from routes.reports    import reports_bp
    from routes.users      import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(stores_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(simulation_bp)
    app.register_blueprint(optimization_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)


# Create trained_models directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'trained_models'), exist_ok=True)

# Application instance (used by Gunicorn and direct run)
app = create_app()

if __name__ == '__main__':
    port = app.config.get('APP_PORT', 5000)
    print(f"\n{'='*50}")
    print(f"  RetailTwin AI starting on http://127.0.0.1:{port}")
    print(f"{'='*50}\n")
    app.run(host='127.0.0.1', port=port, debug=app.config.get('DEBUG', True))
