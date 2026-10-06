"""Category CRUD routes."""

from flask import Blueprint, render_template, request, jsonify
from datetime import date
from models import db
from models.category import Category
from utils.decorators import login_required, admin_required, get_current_user
from utils.validators import validate_required_string

categories_bp = Blueprint('categories', __name__)


@categories_bp.route('/categories')
@login_required
def index():
    current_user = get_current_user()
    return render_template('categories/index.html', current_user=current_user)


@categories_bp.route('/api/categories', methods=['GET'])
@login_required
def api_list():
    categories = Category.query.order_by(Category.category_name).all()
    return jsonify({'success': True, 'data': [c.to_dict() for c in categories]})


@categories_bp.route('/api/categories', methods=['POST'])
@login_required
def api_create():
    data = request.get_json(silent=True) or {}
    name = str(data.get('category_name', '')).strip()
    desc = str(data.get('description', '')).strip()

    if not validate_required_string(name, 100):
        return jsonify({'success': False, 'message': 'Category name is required (max 100 chars).'}), 400

    if Category.query.filter_by(category_name=name).first():
        return jsonify({'success': False, 'message': 'Category name already exists.'}), 409

    cat = Category(category_name=name, description=desc or None, created_date=date.today())
    db.session.add(cat)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Category created', 'data': cat.to_dict()}), 201


@categories_bp.route('/api/categories/<int:category_id>', methods=['GET'])
@login_required
def api_get(category_id):
    cat = Category.query.get_or_404(category_id)
    return jsonify({'success': True, 'data': cat.to_dict()})


@categories_bp.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def api_update(category_id):
    cat  = Category.query.get_or_404(category_id)
    data = request.get_json(silent=True) or {}
    name = str(data.get('category_name', cat.category_name)).strip()
    desc = str(data.get('description', cat.description or '')).strip()

    if not validate_required_string(name, 100):
        return jsonify({'success': False, 'message': 'Category name is required.'}), 400

    existing = Category.query.filter_by(category_name=name).first()
    if existing and existing.category_id != category_id:
        return jsonify({'success': False, 'message': 'Category name already exists.'}), 409

    cat.category_name = name
    cat.description   = desc or None
    db.session.commit()
    return jsonify({'success': True, 'message': 'Category updated', 'data': cat.to_dict()})


@categories_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def api_delete(category_id):
    cat = Category.query.get_or_404(category_id)
    try:
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Category deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Cannot delete: category has products.'}), 409
