from flask import Blueprint, render_template, jsonify # Added jsonify
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

from app.models.quiz import Quiz # Import Quiz model for homepage

@main_bp.route('/')
@main_bp.route('/index')
# @login_required # Homepage should be accessible to guests too
def index():
    # Fetch a few PDFs and Quizzes for the homepage
    # Example: Fetch recent PDFs, or implement a "featured" flag later
    featured_pdfs = PDF.query.order_by(PDF.uploaded_at.desc()).limit(3).all()

    # Example: Fetch quizzes with most questions, or implement "popular" logic later
    # For now, just recent quizzes
    popular_quizzes = Quiz.query.order_by(Quiz.id.desc()).limit(3).all() # Assuming Quiz model is imported

    return render_template('main/index.html', title='Welcome',
                           featured_pdfs=featured_pdfs,
                           popular_quizzes=popular_quizzes)

@main_bp.route('/health')
def health_check():
    """Health check endpoint for Render or other monitoring services."""
    # Optionally, add checks here (e.g., database connectivity)
    # For now, a simple 200 OK is sufficient to indicate the app is running.
    return jsonify(status="ok", message="Application is healthy."), 200

# A simple profile page, also requires login
from flask import current_app, session # For session and app.config
from app.models.pdf import PDF, Purchase
from app.models.user import User
from app import db
# from app.utils.paystack_utils import initialize_transaction, verify_transaction # Commented out
from app.utils.mailer import send_email # For purchase confirmation
import uuid # For generating unique references

from app.models.quiz import QuizAttempt # Ensure QuizAttempt is imported

@main_bp.route('/profile') # This will serve as the User Dashboard
@login_required
def profile():
    user_purchases = Purchase.query.join(PDF, Purchase.pdf_id == PDF.id)\
                               .add_columns(Purchase.timestamp, Purchase.amount_paid, PDF.id.label("pdf_id"), PDF.title.label("pdf_title"))\
                               .filter(Purchase.user_id == current_user.id)\
                               .order_by(Purchase.timestamp.desc()).all()

    user_quiz_attempts = QuizAttempt.query.join(Quiz, QuizAttempt.quiz_id == Quiz.id)\
                                    .add_columns(QuizAttempt.id.label("attempt_id"), QuizAttempt.score, QuizAttempt.attempted_on, Quiz.title.label("quiz_title"))\
                                    .filter(QuizAttempt.user_id == current_user.id)\
                                    .order_by(QuizAttempt.attempted_on.desc()).all()

    return render_template('main/profile.html', title='My Dashboard',
                           user=current_user, purchases=user_purchases,
                           quiz_attempts=user_quiz_attempts)

# Payment Routes
# --------------
@main_bp.route('/checkout/paystack/initiate/<int:pdf_id>', methods=['POST'])
@login_required
def checkout_paystack_initiate(pdf_id):
    pdf_to_purchase = PDF.query.get_or_404(pdf_id)

    if not pdf_to_purchase.is_paid or pdf_to_purchase.price is None or pdf_to_purchase.price <= 0:
        flash("This PDF is not available for purchase or is free.", "info")
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf_id))

    # Check if user already purchased this PDF
    existing_purchase = Purchase.query.filter_by(user_id=current_user.id, pdf_id=pdf_id).first()
    if existing_purchase:
        flash("You have already purchased this PDF.", "info")
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf_id))

    amount_kobo = int(pdf_to_purchase.price * 100) # Convert price to Kobo
    email = current_user.email
    reference = f"pdf_{pdf_id}_user_{current_user.id}_{str(uuid.uuid4())[:8]}" # Unique reference

    # Store reference and pdf_id in session to verify upon callback
    # This is a simple way; a temporary DB table might be more robust for production
    session['paystack_reference'] = reference
    session['paystack_pdf_id'] = pdf_id
    session['paystack_amount_kobo'] = amount_kobo


    callback_url = url_for('main.paystack_callback', _external=True)

    metadata = {
        "pdf_id": pdf_id,
        "user_id": current_user.id,
        "pdf_title": pdf_to_purchase.title,
        "custom_fields": [ # As per Paystack documentation example
            {
                "display_name": "Product",
                "variable_name": "product_name",
                "value": f"PDF: {pdf_to_purchase.title}"
            },
            {
                "display_name": "User Email",
                "variable_name": "user_email",
                "value": current_user.email
            }
        ]
    }

    payment_init_response = initialize_transaction(email, amount_kobo, reference, callback_url, metadata)

    if payment_init_response['status'] and payment_init_response['data'].get('authorization_url'):
        return redirect(payment_init_response['data']['authorization_url'])
    else:
        flash(f"Could not initiate payment: {payment_init_response.get('message', 'Unknown error')}", "danger")
        current_app.logger.error(f"Paystack init failed for user {current_user.id}, pdf {pdf_id}: {payment_init_response}")
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf_id))


@main_bp.route('/checkout/paystack/callback') # Default GET method
def paystack_callback():
    reference = request.args.get('reference') # Paystack usually sends 'trxref' or 'reference'

    if not reference:
        # Paystack might also use 'trxref' if you configured it or based on older APIs
        reference = request.args.get('trxref')
        if not reference:
            flash("Payment callback received without a transaction reference.", "danger")
            current_app.logger.warning("Paystack callback without reference.")
            return redirect(url_for('pdf.marketplace')) # Or a generic error page

    # Retrieve stored reference details (e.g., from session or temp DB)
    # Important: Validate that this reference is one you initiated and not yet processed.
    stored_reference = session.get('paystack_reference')
    pdf_id_for_purchase = session.get('paystack_pdf_id')
    # amount_expected_kobo = session.get('paystack_amount_kobo')

    if not stored_reference or stored_reference != reference or not pdf_id_for_purchase:
        flash("Invalid or missing payment reference in session. Please try the purchase again or contact support if payment was made.", "danger")
        current_app.logger.error(f"Paystack callback with mismatched/missing session reference. Received: {reference}, Session: {stored_reference}")
        return redirect(url_for('pdf.marketplace'))

    verification_response = verify_transaction(reference)

    if verification_response['status'] and verification_response['data'].get('status') == 'success':
        # Payment successful
        pdf_id = verification_response['data'].get('metadata', {}).get('pdf_id', pdf_id_for_purchase)
        user_id = verification_response['data'].get('metadata', {}).get('user_id', current_user.id if current_user.is_authenticated else None)
        amount_paid_kobo = verification_response['data'].get('amount')

        # Additional checks:
        # - Ensure amount paid matches expected amount
        # - Ensure this reference hasn't been processed before to prevent replay attacks

        # For simplicity, assuming pdf_id and user_id from metadata or session are reliable here.
        # A more robust check would use the reference to fetch an internal pending transaction record.

        pdf_instance = PDF.query.get(pdf_id)

        if not pdf_instance:
            flash("Purchased PDF not found. Please contact support.", "danger")
            current_app.logger.error(f"Paystack callback: PDF not found for id {pdf_id} from reference {reference}")
            return redirect(url_for('pdf.marketplace'))

        # Check if purchase already recorded for this reference (idempotency)
        existing_purchase = Purchase.query.filter_by(transaction_reference=reference).first()
        if existing_purchase:
            flash(f"You have already successfully purchased '{pdf_instance.title}'. You can download it now.", "info")
            return redirect(url_for('pdf.pdf_detail', pdf_id=pdf_id))

        new_purchase = Purchase(
            user_id=user_id or current_user.id, # Fallback if not in metadata
            pdf_id=pdf_id,
            transaction_reference=reference, # Store Paystack reference
            amount_paid=(amount_paid_kobo / 100.0) if amount_paid_kobo else pdf_instance.price, # Store amount in major currency unit
            status='success' # Add a status field to Purchase model
        )
        db.session.add(new_purchase)
        db.session.commit()

        # Clear session variables after successful processing
        session.pop('paystack_reference', None)
        session.pop('paystack_pdf_id', None)
        session.pop('paystack_amount_kobo', None)

        # Send confirmation email
        try:
            user_to_notify = User.query.get(user_id or current_user.id)
            if user_to_notify:
                 paystack_receipt_data = verification_response['data'] # Full data from Paystack verification
                 send_email(
                    subject=f"Your Purchase Confirmation for '{pdf_instance.title}'",
                    recipients=[user_to_notify.email],
                    text_body=render_template('email/purchase_confirmation.txt',
                                              pdf=pdf_instance,
                                              purchase=new_purchase,
                                              paystack_data=paystack_receipt_data),
                    html_body=render_template('email/purchase_confirmation.html',
                                              pdf=pdf_instance,
                                              purchase=new_purchase,
                                              paystack_data=paystack_receipt_data)
                )
        except Exception as e:
            current_app.logger.error(f"Failed to send purchase confirmation email for ref {reference}: {e}")


        flash(f"Payment successful! You have purchased '{pdf_instance.title}'.", "success")
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf_id))
    else:
        # Payment failed or verification issue
        flash(f"Payment verification failed: {verification_response.get('message', 'Unknown error')}", "danger")
        current_app.logger.error(f"Paystack verification failed for reference {reference}: {verification_response}")
        # Clear session variables on failure too to allow retry
        session.pop('paystack_reference', None)
        session.pop('paystack_pdf_id', None)
        session.pop('paystack_amount_kobo', None)
        return redirect(url_for('pdf.pdf_detail', pdf_id=pdf_id_for_purchase or 0)) # Redirect to last known PDF or marketplace
