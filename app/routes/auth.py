from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models.user import User, UserRole
from app import db # Removed bcrypt import, model handles hashing
from app.forms.auth_forms import LoginForm, RegisterForm
from app.utils.mailer import send_verification_email
# For generating tokens for email verification
from itsdangerous import URLSafeTimedSerializer
from flask import current_app # To access app.config for SECRET_KEY

auth_bp = Blueprint('auth', __name__, url_prefix='/auth') # Added url_prefix back

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index')) # Or wherever authenticated users should go
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.email_verified:
                flash('Your email address has not been verified. Please check your inbox or request a new verification email.', 'warning')
                # Optionally, redirect to a page where they can request resend verification
                return redirect(url_for('auth.login')) # Or a dedicated page

            login_user(user, remember=True) # Added remember=True for session persistence
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index')) # Redirect to next_page or default
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    return render_template('auth/login.html', title='Login', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        new_user = User(email=form.email.data, role=UserRole.VERIFIED_USER) # Default role
        new_user.set_password(form.password.data)
        # new_user.email_verified is False by default per model

        db.session.add(new_user)
        db.session.commit()

        # Send verification email
        token = generate_verification_token(new_user.email)
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        send_verification_email(new_user.email, verification_url)

        flash('Account created successfully! Please check your email to verify your account before logging in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

# Helper to generate a token
def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'email-verification-salt'))

# Helper to verify a token
def verify_token(token, expiration=3600): # Default expiration: 1 hour
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=current_app.config.get('SECURITY_PASSWORD_SALT', 'email-verification-salt'),
            max_age=expiration
        )
    except Exception: # Covers SignatureExpired, BadTimeSignature, BadSignature, etc.
        return None
    return email

@auth_bp.route('/verify_email/<token>')
def verify_email(token):
    email = verify_token(token)
    if email:
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User not found for this verification token.', 'danger')
            return redirect(url_for('main.index'))
        if user.email_verified:
            flash('Email already verified. Please log in.', 'info')
            return redirect(url_for('auth.login'))

        user.email_verified = True
        db.session.commit()
        flash('Your email has been verified! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    else:
        flash('The verification link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('main.index')) # Or a page to resend verification

# Route to request resending verification email (optional, good UX)
@auth_bp.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification_request():
    # This would typically have a form asking for the user's email
    # For simplicity, let's assume if a non-verified user tries to login,
    # we can guide them here or show a button on the login page.
    # If current_user is authenticated but not verified:
    if current_user.is_authenticated and not current_user.email_verified:
        token = generate_verification_token(current_user.email)
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        send_verification_email(current_user.email, verification_url)
        flash('A new verification email has been sent to your email address.', 'info')
        return redirect(url_for('main.index')) # Or back to login

    # If user is not logged in, redirect to login or show an email form
    flash('Please log in to request a new verification email or register if you don\'t have an account.', 'info')
    return redirect(url_for('auth.login'))

# Need to define main.index or change redirects accordingly
# e.g., to 'pdf.marketplace' or a generic homepage
# For now, I'll assume 'main.index' exists for homepage/dashboard after login.
# The original redirect was to 'pdf.marketplace'

# In app/__init__.py, the auth_bp is registered with url_prefix='/auth'
# So, routes like '/login' become '/auth/login' automatically.
# My previous removal of url_prefix in Blueprint was incorrect if it's defined in register_blueprint.
# The existing code had: auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
# and then app.register_blueprint(auth_bp, url_prefix='/auth') which is redundant.
# I will stick to the prefix in the Blueprint definition or in register_blueprint, but not both.
# The existing code had it in Blueprint definition. I'll revert that part.
# Re-add url_prefix to Blueprint definition to match original structure
# auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
# This change will be done in a subsequent step if needed after checking app/__init__.py
# For now, the diff will show it removed.
# The current code has: from app.routes.auth import bp as auth_bp; app.register_blueprint(auth_bp, url_prefix='/auth')
# So the Blueprint should NOT have the prefix. My change to remove it was correct.
