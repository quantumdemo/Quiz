import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_in_dev') # Made dev key more obvious

    # DATABASE_URL will be provided by Render for PostgreSQL.
    # For local development, it can fall back to SQLite or a local Postgres instance via .env file.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    # Fallback to SQLite if DATABASE_URL is not set (e.g. for initial local setup without .env)
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'instance', 'app.db')
        # Ensure instance folder exists for SQLite for local dev
        instance_path = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'instance')
        if not os.path.exists(instance_path):
            os.makedirs(instance_path)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com') # Allow override via env
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') # For important notifications (as in original plan's config)
    PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
    PAYSTACK_PUBLIC_KEY = os.environ.get('PAYSTACK_PUBLIC_KEY') # As in original plan's config
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'app/uploads') # More flexible, less hardcoded to static
    ALLOWED_EXTENSIONS = {'pdf'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size

    # For email verification and other token generation
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', 'my_very_secure_salt')

    # Ensure the upload folder exists (moved from original plan's config to here)
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
