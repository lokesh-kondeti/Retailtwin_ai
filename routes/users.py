"""User management routes (admin only)."""

from flask import Blueprint, render_template, request, jsonify
from models import db
from models.user import User
from utils.decorators import login_required, admin_required, get_current_user
from utils.validators import validate_email, validate_required_string

users_bp = Blueprint('users', __name__)


@users_bp.route('/users')
@admin_required
def index():
    current_user = get_current_user()
    return render_template('users/index.html', current_user=current_user)


@users_bp.route('/api/users', methods=['GET'])
@admin_required
def api_list():
    users = User.query.order_by(User.name).all()
    return jsonify({'success': True, 'data': [u.to_dict() for u in users]})


@users_bp.route('/api/users', methods=['POST'])
@admin_required
def api_create():
    data     = request.get_json(silent=True) or {}
    name     = str(data.get('name', '')).strip()
    email    = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    phone    = str(data.get('phone', '')).strip()
    role     = str(data.get('role', 'STORE_MANAGER')).upper()

    errors = []
    if not validate_required_string(name, 100): errors.append('Name is required.')
    if not validate_email(email):               errors.append('Valid email is required.')
    if len(password) < 6:                       errors.append('Password must be at least 6 characters.')
    if role not in ('ADMIN', 'STORE_MANAGER'):  errors.append('Invalid role.')
    if errors:
        return jsonify({'success': False, 'message': ' '.join(errors)}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': 'Email already registered.'}), 409

    user = User(name=name, email=email, phone=phone or None, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'User created', 'data': user.to_dict()}), 201


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def api_update(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    name  = str(data.get('name', user.name)).strip()
    phone = str(data.get('phone', user.phone or '')).strip()
    role  = str(data.get('role', user.role)).upper()

    if not validate_required_string(name, 100):
        return jsonify({'success': False, 'message': 'Name is required.'}), 400
    if role not in ('ADMIN', 'STORE_MANAGER'):
        return jsonify({'success': False, 'message': 'Invalid role.'}), 400

    user.name  = name
    user.phone = phone or None
    user.role  = role

    new_password = data.get('password', '')
    if new_password and len(new_password) >= 6:
        user.set_password(new_password)

    db.session.commit()
    return jsonify({'success': True, 'message': 'User updated', 'data': user.to_dict()})


@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete(user_id):
    from flask import session
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'message': 'Cannot delete your own account.'}), 400
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'User deleted'})
