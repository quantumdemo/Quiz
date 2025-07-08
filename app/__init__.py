from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from .config import Config
import os # For path construction

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
csrf = CSRFProtect()

def create_app(config_class=Config): # Added config_class for flexibility
    # Determine the correct template folder path (project_root/templates)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    template_dir = os.path.join(project_root, 'templates')
    # Assuming a root static folder as well, if not, Flask defaults to app/static
    # The ls output did not show a root static/, but app/static/ was created.
    # For now, let Flask default for static or use app.static_folder if needed.
    # Let's assume static files are in app/static as per my earlier creation.
    # Default static_folder is 'static' relative to app instance path (app/static)
    # Default template_folder is 'templates' relative to app instance path (app/templates)
    # Since templates are at root, we must specify.

    app = Flask(__name__, template_folder=template_dir) # Specify template_folder
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Sets the login route
    login_manager.login_message = 'Please log in to access this page.' # Optional: message flashed when @login_required is used
    login_manager.login_message_category = 'info' # Optional: category for the flash message
    bcrypt.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.pdf import pdf_bp
    from app.routes.quiz import quiz_bp
    from app.routes.admin import admin_bp
    from app.routes.main import main_bp # Import main blueprint

    app.register_blueprint(auth_bp) # url_prefix is in the Blueprint object
    app.register_blueprint(pdf_bp)  # Assuming others also define prefix if needed, or it's root
    app.register_blueprint(quiz_bp)
    app.register_blueprint(admin_bp) # url_prefix is likely in this Blueprint too
    app.register_blueprint(main_bp) # Register main blueprint (typically no prefix or '/')

    # Context processors
    import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.utcnow()} # Provides 'now' to all templates

    return app
