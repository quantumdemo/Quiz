import enum
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(enum.Enum):
    ADMIN = 'admin'
    VERIFIED_USER = 'verified_user'
    # GUEST users are typically unauthenticated users, so not a DB role here.

@login_manager.user_loader
def load_user(user_id):
    # Updated to use the new SQLAlchemy 2.0 Session.get() method
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.VERIFIED_USER, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Users are active by default
    email_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    # PDFs uploaded by this user (if this user is an admin/uploader)
    # 'uploaded_pdfs' backref is defined in PDF model's 'uploader' relationship

    # Reviews written by this user
    reviews = db.relationship('Review', backref='user', lazy='dynamic', foreign_keys='Review.user_id')

    # PDFs purchased by this user
    purchases = db.relationship('Purchase', backref='user', lazy='dynamic', foreign_keys='Purchase.user_id')

    # Quiz attempts by this user
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy='dynamic', foreign_keys='QuizAttempt.user_id')


    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    # Flask-Login properties
    # is_active is already a column
    # is_authenticated is True if they are logged in (handled by Flask-Login)
    # is_anonymous is False for logged-in users (handled by Flask-Login)

    # def get_id(self): # Provided by UserMixin
    #     return str(self.id)
