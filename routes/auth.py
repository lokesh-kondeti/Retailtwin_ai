"""Authentication routes — login and logout."""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from models.user import User
from utils.validators import validate_email, validate_required_string

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and form handler."""
    # Already logged in → go to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Backend validation
        errors = []
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        if not validate_required_string(password):
            errors.append('Password is required.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/login.html', email=email), 400

        # Look up user
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html', email=email), 401

        # Persist session
        session.permanent = True
        session['user_id'] = user.user_id
        session['name']    = user.name
        session['email']   = user.email
        session['role']    = user.role

        flash(f'Welcome back, {user.name}!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    """Clear session and redirect to login."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# API login endpoint (JSON) for potential AJAX use
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    data     = request.get_json(silent=True) or {}
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not validate_email(email) or not validate_required_string(password):
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

    session['user_id'] = user.user_id
    session['name']    = user.name
    session['email']   = user.email
    session['role']    = user.role

    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})
