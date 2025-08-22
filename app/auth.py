from functools import wraps
from flask import session, redirect, url_for, flash, request
from app.models import User, db
from datetime import datetime

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this feature.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current logged-in user or None"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

def login_user(user):
    """Log in a user by storing user ID in session"""
    session['user_id'] = user.id
    session['username'] = user.username
    session['full_name'] = user.full_name
    user.last_login = datetime.utcnow()
    db.session.commit()

def logout_user():
    """Log out the current user by clearing session"""
    session.clear()

def is_logged_in():
    """Check if a user is currently logged in"""
    return 'user_id' in session and session['user_id'] is not None
