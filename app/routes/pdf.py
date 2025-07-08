from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app, jsonify # Added jsonify
from flask_login import login_required, current_user
# werkzeug.utils secure_filename is not used here anymore, but kept if old upload route is not removed
from werkzeug.utils import secure_filename
import os
from app.models.pdf import PDF, Purchase
from app.models.review import Review # Import Review model
from app.forms.pdf_forms import SearchForm, ReviewForm # Import forms
from app import db
from sqlalchemy import or_ # For search queries

pdf_bp = Blueprint('pdf', __name__) # url_prefix='/pdf' is set in app.register_blueprint

# The old /upload route here is superseded by admin.upload_pdf.
# It should ideally be removed to avoid confusion.
# For now, I'll leave it commented out or remove later if confirmed.
# @pdf_bp.route('/upload', methods=['GET', 'POST'])
# @login_required
# def upload_pdf(): ... (old code) ...

@pdf_bp.route('/') # Changed marketplace to be the root of pdf_bp
@pdf_bp.route('/marketplace')
def marketplace():
    form = SearchForm(request.args) # Populate form from query parameters for GET requests
    page = request.args.get('page', 1, type=int)

    query_obj = PDF.query.order_by(PDF.uploaded_at.desc())

    search_term = form.query.data
    category_filter = form.category.data
    # price_filter = request.args.get('price') # Example for direct arg, or add to form

    if search_term:
        search_filter = or_(
            PDF.title.ilike(f'%{search_term}%'),
            PDF.description.ilike(f'%{search_term}%'),
            PDF.tags.ilike(f'%{search_term}%')
        )
        query_obj = query_obj.filter(search_filter)

    if category_filter:
        query_obj = query_obj.filter(PDF.category.ilike(f'%{category_filter}%'))

    # Example: Filtering by price (is_free / is_paid)
    # if price_filter == 'free':
    #     query_obj = query_obj.filter(PDF.is_paid == False)
    # elif price_filter == 'paid':
    #     query_obj = query_obj.filter(PDF.is_paid == True)

    pdfs = query_obj.paginate(page=page, per_page=current_app.config.get('PDFS_PER_PAGE', 9))

    # Get distinct categories for filter dropdown (optional enhancement)
    categories = db.session.query(PDF.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]] # Filter out None/empty and extract string

    return render_template('pdf/marketplace.html', pdfs=pdfs, form=form, title="PDF Marketplace", categories=categories)

@pdf_bp.route('/<int:pdf_id>') # Route for viewing a single PDF
def pdf_detail(pdf_id):
    pdf = PDF.query.get_or_404(pdf_id)
    reviews = Review.query.filter_by(pdf_id=pdf.id).order_by(Review.created_at.desc()).all()
    review_form = ReviewForm() # For submitting a new review

    # Check if current user has already reviewed this PDF
    user_has_reviewed = False
    if current_user.is_authenticated:
        existing_review = Review.query.filter_by(user_id=current_user.id, pdf_id=pdf.id).first()
        if existing_review:
            user_has_reviewed = True
            # Optionally, pass the existing review to the template if you want to allow editing it
            # review_form = ReviewForm(obj=existing_review) # If editing is allowed

    return render_template('pdf/pdf_detail.html', pdf=pdf, reviews=reviews,
                           review_form=review_form, user_has_reviewed=user_has_reviewed, title=pdf.title)

@pdf_bp.route('/<int:pdf_id>/review', methods=['POST'])
@login_required
def submit_review(pdf_id):
    pdf = PDF.query.get_or_404(pdf_id)
    form = ReviewForm()
    if form.validate_on_submit():
        existing_review = Review.query.filter_by(user_id=current_user.id, pdf_id=pdf.id).first()
        if existing_review:
            flash('You have already reviewed this PDF. You can edit your existing review.', 'info')
            # Optionally, update existing review:
            # existing_review.rating = int(form.rating.data)
            # existing_review.comment = form.comment.data
            # db.session.commit()
            # flash('Your review has been updated.', 'success')
        else:
            new_review = Review(
                rating=int(form.rating.data),
                comment=form.comment.data,
                user_id=current_user.id,
                pdf_id=pdf.id
            )
            db.session.add(new_review)
            db.session.commit()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # For AJAX, return JSON. Include the new review HTML or data to append.
                # For simplicity, just success and new review data. Client will format.
                return jsonify({
                    'status': 'success',
                    'message': 'Review submitted successfully!',
                    'review': {
                        'rating': new_review.rating,
                        'comment': new_review.comment,
                        'user_email': current_user.email, # Assuming current_user is the reviewer
                        'created_at': new_review.created_at.strftime('%Y-%m-%d %H:%M')
                    }
                }), 200
            else:
                flash('Your review has been submitted successfully!', 'success')
                return redirect(url_for('pdf.pdf_detail', pdf_id=pdf.id))

    # If form validation fails
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Collect form errors to send back as JSON
        errors = {field.label.text: field.errors for field in form if field.errors}
        return jsonify({'status': 'error', 'message': 'Validation failed.', 'errors': errors}), 400
    else:
        # For non-AJAX, re-render the detail page with errors
        reviews = Review.query.filter_by(pdf_id=pdf.id).order_by(Review.created_at.desc()).all()
        user_has_reviewed = True # Since they tried to submit
        return render_template('pdf/pdf_detail.html', pdf=pdf, reviews=reviews,
                               review_form=form, user_has_reviewed=user_has_reviewed, title=pdf.title)


@pdf_bp.route('/download/<int:pdf_id>')
@login_required
def download(pdf_id):
    pdf = PDF.query.get_or_404(pdf_id)

    # Ensure UPLOAD_FOLDER is correctly configured and accessible
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    if not upload_folder or not os.path.isdir(upload_folder):
        current_app.logger.error(f"UPLOAD_FOLDER is not configured or not a directory: {upload_folder}")
        flash("File download service is currently unavailable. Please try again later.", "danger")
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf.id))

    if pdf.is_paid:
        # User must have a purchase record to download a paid PDF
        purchase = Purchase.query.filter_by(user_id=current_user.id, pdf_id=pdf.id).first()
        if not purchase:
            flash('You need to purchase this PDF to download it.', 'danger')
            return redirect(url_for('pdf.pdf_detail', pdf_id=pdf.id))
    else:
        # For free PDFs, log the download as a "purchase" with price 0 if not already logged
        # This helps maintain a download history for free items too.
        existing_access = Purchase.query.filter_by(user_id=current_user.id, pdf_id=pdf.id).first()
        if not existing_access:
            free_purchase = Purchase(user_id=current_user.id, pdf_id=pdf.id) # price defaults to null or can be set to 0
            db.session.add(free_purchase)
            db.session.commit()
            current_app.logger.info(f"User {current_user.id} downloaded free PDF {pdf.id}")

    # Securely send the file
    # Ensure pdf.filename is just the filename, not a path, to prevent directory traversal
    # UPLOAD_FOLDER should be an absolute path or resolved correctly.
    # os.path.join is good, but ensure its arguments are safe.
    safe_filename = secure_filename(pdf.filename) # Should already be secure, but double check

    if not os.path.exists(os.path.join(upload_folder, safe_filename)):
        current_app.logger.error(f"File not found for PDF {pdf.id}: {safe_filename} in {upload_folder}")
        flash("The requested file could not be found. Please contact support.", "danger")
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf.id))

    return send_from_directory(upload_folder, safe_filename, as_attachment=True)
