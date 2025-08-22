from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, db
from app.auth import login_user, logout_user, get_current_user
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me')
        
        if not username_or_email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('auth/login.html')
        
        # Check if input is email or username
        if '@' in username_or_email:
            user = User.query.filter_by(email=username_or_email).first()
        else:
            user = User.query.filter_by(username=username_or_email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'danger')
                return render_template('auth/login.html')
            
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        student_id = request.form.get('student_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([username, email, full_name, password, confirm_password]):
            flash('Please fill in all required fields.', 'danger')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')
        
        # Email validation
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('auth/register.html')
        
        # Username validation
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'danger')
            return render_template('auth/register.html')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            flash('Username can only contain letters, numbers, and underscores.', 'danger')
            return render_template('auth/register.html')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email or login.', 'danger')
            return render_template('auth/register.html')
        
        if student_id and User.query.filter_by(student_id=student_id).first():
            flash('Student ID already registered.', 'danger')
            return render_template('auth/register.html')
        
        # Create new user
        try:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                student_id=student_id if student_id else None
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            print(f"Registration error: {str(e)}")
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    user = get_current_user()
    if user:
        flash(f'Goodbye, {user.full_name}!', 'info')
    logout_user()
    return redirect(url_for('main.index'))

@auth_bp.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/profile.html', user=user)
