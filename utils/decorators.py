"""
Authentication decorators for route protection.
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, request, flash


def login_required(f):
    """Redirect unauthenticated users to login. Returns 401 for API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Allow only ADMIN role. Returns 403 for unauthorized users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'ADMIN':
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin access required'}), 403
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    """Return basic session info as a dict, or None if not logged in."""
    if 'user_id' not in session:
        return None
    return {
        'user_id': session.get('user_id'),
        'name':    session.get('name'),
        'email':   session.get('email'),
        'role':    session.get('role'),
    }
