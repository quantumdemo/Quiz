from app import db
from datetime import datetime

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Added nullable=False for consistency
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdf.id'), nullable=False) # Corrected to lowercase 'pdf.id' and added nullable=False
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text) # Nullable is fine for comment
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to User (author of the review) is implicitly handled by backref in User model if 'user' is defined there.
    # However, it's good to define it explicitly if needed or if the backref isn't named 'user'.
    # The User model has: reviews = db.relationship('Review', backref='user', lazy='dynamic', foreign_keys='Review.user_id')
    # So, `review.user` will work. No change needed here for that specific relationship access.

    # Relationship to PDF (the PDF being reviewed)
    # pdf = db.relationship('PDF', backref=db.backref('reviews_on_pdf', lazy='dynamic'))
    # This is already handled by the 'reviews' relationship in the PDF model:
    # PDF.reviews = db.relationship('Review', backref='pdf', lazy='dynamic', cascade="all, delete-orphan")
    # So, `review.pdf` will work.

    def __repr__(self):
        return f"<Review {self.id} - PDF {self.pdf_id} by User {self.user_id} ({self.rating} stars)>"
