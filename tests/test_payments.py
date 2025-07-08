import pytest
from flask import url_for, session, request
from unittest.mock import patch, MagicMock

# Explicitly import modules whose contents are being patched at source
import app.utils.paystack_utils
import app.utils.mailer

from app.models.pdf import PDF, Purchase
from app.models.user import User, UserRole
from app import db
from tests.conftest import SAMPLE_PAID_PDF_DATA, SAMPLE_FREE_PDF_DATA


def test_initiate_payment_unauthenticated(test_client, test_app, setup_pdfs):
    """Test initiating payment when not logged in."""
    pdf_ids = setup_pdfs
    with test_app.app_context():
        initiate_url = url_for('main.checkout_paystack_initiate', pdf_id=pdf_ids['paid_pdf_id'])

    response = test_client.post(initiate_url, follow_redirects=False)
    assert response.status_code == 302 # Should redirect to login
    with test_app.app_context():
        assert url_for('auth.login', _external=False) in response.location.split('?')[0]

@patch('app.utils.paystack_utils.initialize_transaction') # Patch at source
def test_initiate_payment_success(mock_initialize_transaction, test_client, test_app, logged_in_user, setup_pdfs):
    """Test successful payment initiation for a paid PDF."""
    pdf_ids = setup_pdfs
    mock_initialize_transaction.return_value = {
        'status': True,
        'data': {'authorization_url': 'https://paystack.com/pay/mock_auth_url', 'reference': 'test_ref_123'},
        'message': 'Authorization URL created'
    }

    with test_app.test_request_context(): # Ensure session is available
        with test_app.app_context():
            initiate_url = url_for('main.checkout_paystack_initiate', pdf_id=pdf_ids['paid_pdf_id'])

        response = test_client.post(initiate_url, follow_redirects=False) # User is logged in by fixture

        assert response.status_code == 302 # Redirect to Paystack
        assert response.location == 'https://paystack.com/pay/mock_auth_url'

        # Check session variables
        assert session.get('paystack_reference') == 'test_ref_123'
        assert session.get('paystack_pdf_id') == pdf_ids['paid_pdf_id']
        assert session.get('paystack_amount_kobo') == int(SAMPLE_PAID_PDF_DATA['price'] * 100)

        # Check that initialize_transaction was called correctly
        # User object is available via current_user in the route after logged_in_user fixture
        user = User.query.filter_by(email='testuser@test.com').first()
        mock_initialize_transaction.assert_called_once()
        args, kwargs = mock_initialize_transaction.call_args
        assert kwargs['email'] == user.email
        assert kwargs['amount_kobo'] == int(SAMPLE_PAID_PDF_DATA['price'] * 100)
    # The reference is generated in the route, so we can't easily assert its exact value here
    # unless we also mock uuid.uuid4() or make the reference predictable in tests.
    # For now, checking that it was called with the other correct params is good.
    # assert kwargs['reference'] == 'test_ref_123' # This was from the mock return, not call arg.

@patch('app.utils.paystack_utils.initialize_transaction') # Patch at source
def test_initiate_payment_for_free_pdf(mock_initialize_transaction, test_client, test_app, logged_in_user, setup_pdfs):
    """Test trying to initiate payment for a free PDF."""
    pdf_ids = setup_pdfs
    with test_app.app_context():
        initiate_url = url_for('main.checkout_paystack_initiate', pdf_id=pdf_ids['free_pdf_id'])
        detail_url = url_for('pdf.pdf_detail', pdf_id=pdf_ids['free_pdf_id'])

    response = test_client.post(initiate_url, follow_redirects=True)
    assert response.status_code == 200 # Should redirect back to detail page
    assert request.path == detail_url # Check we landed on the detail page
    assert b"This PDF is not available for purchase or is free." in response.data
    mock_initialize_transaction.assert_not_called() # This mock is for the test_initiate_payment_for_free_pdf

# Need to ensure the mock target for test_initiate_payment_for_free_pdf was also corrected.
# It was @patch('app.routes.main.initialize_transaction') before, should be app.utils.paystack_utils
# The previous diff only showed the change for test_initiate_payment_success.
# Let's assume it was already corrected. If not, the error would persist for that specific test.
# The error message "AttributeError: <module 'app.routes.main' from '/app/app/routes/main.py'> does not have the attribute 'initialize_transaction'"
# for test_initiate_payment_for_free_pdf confirms its patch target is still wrong.

@patch('app.utils.paystack_utils.verify_transaction')   # Patch at source
@patch('app.utils.mailer.send_email')                   # Patch at source
def test_paystack_callback_success(mock_send_email, mock_verify_transaction, test_client, test_app, setup_pdfs):
    """Test successful Paystack callback."""
    pdf_ids = setup_pdfs
    user = User.query.filter_by(email='testuser@test.com').first() # Assuming logged_in_user fixture is not used or callback is independent

    # Simulate session data that would have been set during initiation
    with test_client.session_transaction() as sess:
        sess['paystack_reference'] = 'callback_ref_success'
        sess['paystack_pdf_id'] = pdf_ids['paid_pdf_id']
        sess['paystack_amount_kobo'] = int(SAMPLE_PAID_PDF_DATA['price'] * 100)

    mock_verify_transaction.return_value = {
        'status': True,
        'data': {
            'status': 'success',
            'reference': 'callback_ref_success',
            'amount': int(SAMPLE_PAID_PDF_DATA['price'] * 100), # Amount in Kobo
            'metadata': {'pdf_id': pdf_ids['paid_pdf_id'], 'user_id': user.id}
        },
        'message': 'Verification successful'
    }

    with test_app.app_context():
        callback_url = url_for('main.paystack_callback', reference='callback_ref_success')
        detail_url = url_for('pdf.pdf_detail', pdf_id=pdf_ids['paid_pdf_id'])

    response = test_client.get(callback_url, follow_redirects=True)
    assert response.status_code == 200
    assert request.path == detail_url # Should redirect to PDF detail page
    assert b"Payment successful!" in response.data

    # Verify Purchase record
    with test_app.app_context():
        purchase = Purchase.query.filter_by(transaction_reference='callback_ref_success').first()
        assert purchase is not None
        assert purchase.pdf_id == pdf_ids['paid_pdf_id']
        assert purchase.user_id == user.id
        assert purchase.status == 'success'
        assert purchase.amount_paid == SAMPLE_PAID_PDF_DATA['price']

    # Verify email was called
    mock_send_email.assert_called_once()
    args_email, kwargs_email = mock_send_email.call_args
    assert kwargs_email['subject'] == f"Your Purchase Confirmation for '{SAMPLE_PAID_PDF_DATA['title']}'"
    assert user.email in kwargs_email['recipients']

    # Verify session variables are cleared
    with test_client.session_transaction() as sess:
        assert 'paystack_reference' not in sess
        assert 'paystack_pdf_id' not in sess

# More tests needed:
# - test_initiate_payment_already_purchased
# - test_initiate_payment_paystack_api_error
# - test_paystack_callback_failed_verification
# - test_paystack_callback_mismatched_reference
# - test_paystack_callback_no_reference_in_session
# - test_paystack_callback_idempotency (already purchased via this ref)
# - test_paystack_callback_amount_mismatch (if checking amount)
