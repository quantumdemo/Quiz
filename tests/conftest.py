import pytest
from app import create_app, db
from app.models.user import User, UserRole
# Import all models to ensure they are registered with SQLAlchemy before db.create_all()
from app.models.pdf import PDF, Purchase
from app.models.quiz import Quiz, Question, QuizAttempt
from app.models.review import Review

@pytest.fixture(scope='module')
def test_app():
    """Create and configure a new app instance for each test module."""
    # Setup Flask app for testing
    app = create_app() # Using default Config which should point to a test DB if configured
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", # Use in-memory SQLite for tests
        "WTF_CSRF_ENABLED": False, # Disable CSRF for easier form testing
        "LOGIN_DISABLED": False, # Ensure login is enabled for auth tests
        "MAIL_SUPPRESS_SEND": True, # Suppress actual email sending during tests
        "SERVER_NAME": "localhost.localdomain", # For url_for to work without active request context
        "MAIL_USERNAME": "test@example.com", # Default for tests
        "MAIL_DEFAULT_SENDER": ("Test App", "noreply@example.com"), # Default for tests
        "MAIL_SERVER": "localhost", # Prevent real SMTP attempts during tests
        "MAIL_PORT": 1025,          # Common port for local test SMTP servers (like smtpd.DebuggingServer)
        "MAIL_USE_TLS": False,
        "MAIL_USE_SSL": False,
    })

    with app.app_context():
        db.create_all()
        # Create a default admin user, ensuring email is verified for easier login testing
        admin_user = User.query.filter_by(email='admin@test.com').first()
        if not admin_user:
            admin = User(email='admin@test.com', role=UserRole.ADMIN, email_verified=True)
            admin.set_password('adminpass')
            db.session.add(admin)
        elif not admin_user.email_verified: # Ensure existing test admin is verified
            admin_user.email_verified = True

        # Create a default regular user, ensuring email is verified
        regular_user = User.query.filter_by(email='testuser@test.com').first()
        if not regular_user:
            user = User(email='testuser@test.com', role=UserRole.VERIFIED_USER, email_verified=True)
            user.set_password('testpass')
            db.session.add(user)
        elif not regular_user.email_verified: # Ensure existing test user is verified
            regular_user.email_verified = True

        db.session.commit()


    yield app

    # Teardown: drop all tables after tests are done for the module
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='module')
def test_client(test_app):
    """A test client for the app."""
    return test_app.test_client()


@pytest.fixture(scope='function') # Use function scope if DB changes per test
def init_database(test_app):
    """Reinitialize database for each test function if needed, or manage transactions."""
    with test_app.app_context():
        db.create_all() # Ensure tables are there
        yield db # Provide the db session to tests
        # For function scope, you might want to clean up specific tables or use transactions
        # db.session.remove()
        # db.drop_all() # This is too broad for function scope if module setup is used

# If you need to log in a user for certain tests:
@pytest.fixture(scope='function')
def logged_in_user(test_client):
    # Log in a predefined user
    test_client.post('/auth/login', data={
        'email': 'testuser@test.com',
        'password': 'testpass'
    }, follow_redirects=True)
    yield
    # Log out after the test
    test_client.get('/auth/logout', follow_redirects=True)

# --- Sample Data for Multiple Test Files ---
from decimal import Decimal
from app.models.pdf import PDF as PDFModel, Purchase as PurchaseModel # Alias to avoid pytest name collision

SAMPLE_PAID_PDF_DATA = {
    'title': 'Test Paid PDF Conftest', # Renamed slightly to distinguish if needed
    'description': 'A PDF for testing payments, from conftest.',
    'filename': 'test_paid_conftest.pdf',
    'is_paid': True,
    'price': Decimal('10.00'),
    'category': 'Testing',
    'tags': 'paid,test',
    'uploader_id': None # Will be set to admin user in tests
}
SAMPLE_FREE_PDF_DATA = {
    'title': 'Test Free PDF Conftest',
    'description': 'A free PDF, from conftest.',
    'filename': 'test_free_conftest.pdf',
    'is_paid': False,
    'price': None,
    'category': 'Testing',
    'tags': 'free,test',
    'uploader_id': None
}

@pytest.fixture(scope='function') # Function scope to ensure clean DB for tests needing specific PDF states
def setup_pdfs(test_app): # test_app fixture ensures app context
    with test_app.app_context():
        admin = User.query.filter_by(email='admin@test.com').first()
        # This admin should exist from the module-scoped test_app fixture's initial setup.
        # If not, or if that setup is removed, create here:
        if not admin:
            admin = User(email='admin@test.com', role=UserRole.ADMIN, email_verified=True)
            admin.set_password('adminpass') # Ensure password consistency
            db.session.add(admin)
            db.session.commit() # Commit to get admin.id if newly created

        # Clean up specific models before seeding for this function-scoped fixture
        # PDFModel.query.delete()
        # PurchaseModel.query.delete()
        # This might be too aggressive if other tests rely on pre-existing data not cleaned by module teardown.
        # For now, assume tests handle their own specific data needs or build upon conftest's base users.
        # A more targeted cleanup might be needed if tests interfere.
        # Let's try creating PDFs without deleting all existing ones first. If filename is unique, it's fine.

        paid_pdf_data = {**SAMPLE_PAID_PDF_DATA, 'uploader_id': admin.id}
        paid_pdf = PDFModel.query.filter_by(filename=paid_pdf_data['filename']).first()
        if not paid_pdf:
            paid_pdf = PDFModel(**paid_pdf_data)
            db.session.add(paid_pdf)

        free_pdf_data = {**SAMPLE_FREE_PDF_DATA, 'uploader_id': admin.id}
        free_pdf = PDFModel.query.filter_by(filename=free_pdf_data['filename']).first()
        if not free_pdf:
            free_pdf = PDFModel(**free_pdf_data)
            db.session.add(free_pdf)

        db.session.commit()

        # Return IDs of the specifically created/ensured PDFs for this fixture run
        return {
            'paid_pdf_id': paid_pdf.id,
            'free_pdf_id': free_pdf.id,
            'admin_id': admin.id
        }

@pytest.fixture(scope='function')
def logged_in_admin(test_client):
    # Log in a predefined admin user
    test_client.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'adminpass'
    }, follow_redirects=True)
    yield
    # Log out after the test
    test_client.get('/auth/logout', follow_redirects=True)
