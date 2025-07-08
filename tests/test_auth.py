import pytest
from flask import url_for, get_flashed_messages
from app.models.user import User, UserRole
from app import db

# Note: All test functions that use url_for now also take test_app fixture
# and wrap url_for calls within test_app.app_context().

def test_get_login_page(test_client, test_app):
    """Test that the login page loads."""
    with test_app.app_context():
        url = url_for('auth.login')
    response = test_client.get(url)
    assert response.status_code == 200
    assert b"Login" in response.data
    assert b"Email" in response.data
    assert b"Password" in response.data

def test_get_register_page(test_client, test_app):
    """Test that the register page loads."""
    with test_app.app_context():
        url = url_for('auth.register')
    response = test_client.get(url)
    assert response.status_code == 200
    assert b"Register" in response.data
    assert b"Email" in response.data
    assert b"Password" in response.data
    assert b"Confirm Password" in response.data

def test_successful_registration(test_client, test_app):
    """Test new user registration."""
    with test_app.app_context():
        url = url_for('auth.register')
    response = test_client.post(url, data={
        'email': 'newuser@example.com',
        'password': 'newpassword',
        'confirm_password': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Account created successfully!" in response.data

    with test_app.app_context():
        user = User.query.filter_by(email='newuser@example.com').first()
        assert user is not None
        assert user.email == 'newuser@example.com'
        assert user.email_verified is False
        assert user.role == UserRole.VERIFIED_USER

def test_registration_existing_email(test_client, test_app):
    """Test registration with an email that already exists."""
    with test_app.app_context():
        register_url = url_for('auth.register')

    # First, register a user
    test_client.post(register_url, data={
        'email': 'existing@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)

    # Try to register again with the same email
    response = test_client.post(register_url, data={
        'email': 'existing@example.com',
        'password': 'anotherpassword',
        'confirm_password': 'anotherpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"An account with this email address already exists" in response.data

def test_successful_login_logout(test_client, test_app):
    """Test login with correct credentials and then logout."""
    with test_app.app_context():
        user = User.query.filter_by(email='testuser@test.com').first()
        if user: # User is created in conftest, already verified
            pass # No change needed here, already verified in conftest

        login_url = url_for('auth.login')
        logout_url = url_for('auth.logout')

    response_login = test_client.post(login_url, data={
        'email': 'testuser@test.com',
        'password': 'testpass'
    }, follow_redirects=True)

    assert response_login.status_code == 200
    assert b"Logged in successfully!" in response_login.data
    assert b"Logout" in response_login.data

    response_logout = test_client.get(logout_url, follow_redirects=True)
    assert response_logout.status_code == 200
    assert b"You have been logged out successfully." in response_logout.data
    assert b"Login" in response_logout.data

def test_login_incorrect_password(test_client, test_app):
    """Test login with incorrect password."""
    with test_app.app_context():
        url = url_for('auth.login')
    response = test_client.post(url, data={
        'email': 'testuser@test.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_login_nonexistent_user(test_client, test_app):
    """Test login with an email that does not exist."""
    with test_app.app_context():
        url = url_for('auth.login')
    response = test_client.post(url, data={
        'email': 'nosuchuser@example.com',
        'password': 'anypassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data

def test_login_unverified_email(test_client, test_app):
    """Test login attempt with an unverified email."""
    unverified_email = 'unverified@example.com'
    with test_app.app_context():
        # Ensure this user is not present or is unverified
        existing_user = User.query.filter_by(email=unverified_email).first()
        if existing_user:
            existing_user.email_verified = False
        else:
            unverified_user = User(email=unverified_email, email_verified=False)
            unverified_user.set_password('password')
            db.session.add(unverified_user)
        db.session.commit()

        login_url = url_for('auth.login')

    response = test_client.post(login_url, data={
        'email': unverified_email,
        'password': 'password'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your email address has not been verified" in response.data

def test_email_verification(test_client, test_app):
    """Test the email verification link."""
    user_to_verify_email = 'verifythis@example.com'
    token = None
    with test_app.app_context():
        # Ensure user exists and is unverified
        user = User.query.filter_by(email=user_to_verify_email).first()
        if not user:
            user = User(email=user_to_verify_email, email_verified=False)
            user.set_password('password')
            db.session.add(user)
        else:
            user.email_verified = False
        db.session.commit()

        from app.routes.auth import generate_verification_token
        token = generate_verification_token(user_to_verify_email)

        verify_url = url_for('auth.verify_email', token=token)

    response = test_client.get(verify_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your email has been verified!" in response.data

    with test_app.app_context():
        verified_user = User.query.filter_by(email=user_to_verify_email).first()
        assert verified_user is not None
        assert verified_user.email_verified is True

def test_email_verification_invalid_token(test_client, test_app):
    """Test email verification with an invalid token."""
    with test_app.app_context():
        url = url_for('auth.verify_email', token="invalidtoken")
    response = test_client.get(url, follow_redirects=True)
    assert response.status_code == 200
    assert b"The verification link is invalid or has expired." in response.data

def test_access_protected_route_unauthenticated(test_client, test_app):
    """Test accessing a protected route when not logged in."""
    with test_app.app_context():
        # main.profile is decorated with @login_required
        protected_url = url_for('main.profile')
        login_url_expected = url_for('auth.login', _external=False)

    response = test_client.get(protected_url, follow_redirects=False)
    assert response.status_code == 302
    assert response.location.split('?')[0] == login_url_expected

def test_access_protected_route_authenticated(test_client, test_app, logged_in_user):
    """Test accessing a protected route (user dashboard/profile) when logged in."""
    # logged_in_user fixture handles login using 'testuser@test.com'
    with test_app.app_context():
        dashboard_url = url_for('main.profile') # Target the actual user dashboard

    response = test_client.get(dashboard_url)
    assert response.status_code == 200
    assert b"My Dashboard" in response.data # Title of the profile page
    assert b"testuser@test.com" in response.data # User's email
    assert b"Role:" in response.data and b"Verified User" in response.data # Check for role label and value
    assert b"Email Verified:" in response.data
    # The testuser@test.com from conftest is email_verified=True
    assert b"Yes" in response.data # Check for "Yes" indicating verified
