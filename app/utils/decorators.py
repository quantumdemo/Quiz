from functools import wraps
from flask_login import current_user
from flask import flash, redirect, url_for, request # Added request

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login', next=request.path))
        if not current_user.is_admin: # Use the is_admin property from User model
            flash('This area is restricted to administrators only.', 'danger')
            return redirect(url_for('main.index')) # Or a more appropriate page like user's dashboard
        return f(*args, **kwargs)
    return decorated_function
