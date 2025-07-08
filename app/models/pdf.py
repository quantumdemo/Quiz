from app import db
from datetime import datetime

class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True) # Added category
    tags = db.Column(db.String(255), nullable=True) # Added tags (comma-separated or similar)

    # filename will store the actual name of the PDF file as stored on the server
    # This name should be secured to prevent path traversal or direct access issues.
    # e.g., using uuid generated names.
    filename = db.Column(db.String(255), nullable=False, unique=True)
    cover_image_filename = db.Column(db.String(255), nullable=True) # Added cover image filename

    is_paid = db.Column(db.Boolean, default=False, nullable=False) # is_free would be not is_paid
    price = db.Column(db.Numeric(10, 2), nullable=True) # Added price, relevant if is_paid is True

    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Link to the user who uploaded it
    # For admin-only uploads, this could be nullable or always set to an admin's ID.
    # If nullable=False, a default admin or system user ID might be needed.
    # For now, nullable=True allows flexibility or system-owned PDFs.

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    uploader = db.relationship('User', backref=db.backref('uploaded_pdfs', lazy='dynamic'))
    reviews = db.relationship('Review', backref='pdf', lazy='dynamic', cascade="all, delete-orphan")
    purchases = db.relationship('Purchase', backref='pdf', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PDF {self.id}: {self.title}>"

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Fields for payment integration
    transaction_reference = db.Column(db.String(100), unique=True, nullable=True) # Paystack reference, or null for free "purchases"
    amount_paid = db.Column(db.Numeric(10, 2), nullable=True) # Actual amount paid, can be 0 for free
    status = db.Column(db.String(50), default='pending', nullable=False) # e.g., pending, success, failed, free_download

    # Relationships
    # user = db.relationship('User', backref='purchases') # backref already defined in User model
    # pdf = db.relationship('PDF', backref='purchases') # backref already defined in PDF model

    def __repr__(self):
        return f"<Purchase {self.id} - PDF {self.pdf_id} by User {self.user_id}, Status: {self.status}>"
