# from flask import current_app
# from paystackapi.paystack import Paystack
# from paystackapi.transaction import Transaction as PaystackTransaction
# from paystackapi.base import PaystackAPIError

# def get_paystack_client():
#     """Initializes and returns a Paystack client instance."""
#     secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
#     if not secret_key:
#         current_app.logger.error("Paystack secret key is not configured.")
#         return None
#     Paystack.secret_key = secret_key
#     return Paystack()

# def initialize_transaction(email: str, amount_kobo: int, reference: str, callback_url: str, metadata: dict = None):
#     """
#     Initializes a Paystack transaction.
#     """
#     secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
#     if not secret_key:
#         current_app.logger.error("Paystack secret key is not configured for initialize_transaction.")
#         return {'status': False, 'message': 'Payment system not configured.'}
#     Paystack.secret_key = secret_key

#     try:
#         response_data = PaystackTransaction.initialize(
#             reference=reference,
#             amount=amount_kobo,
#             email=email,
#             callback_url=callback_url,
#             metadata=metadata or {}
#         )
#         return {'status': True, 'data': response_data, 'message': "Authorization URL created"}
#     except PaystackAPIError as e:
#         current_app.logger.error(f"Paystack API Error during initialization: {e.strerror if hasattr(e, 'strerror') else str(e)}")
#         error_detail = e.strerror if hasattr(e, 'strerror') else str(e)
#         return {'status': False, 'message': f"Paystack Error: {error_detail}", 'data': e.data if hasattr(e, 'data') else None}
#     except Exception as e:
#         current_app.logger.error(f"Unexpected error during Paystack initialization: {e}", exc_info=True)
#         return {'status': False, 'message': f"An unexpected payment error occurred: {str(e)}"}

# def verify_transaction(reference: str):
#     """
#     Verifies a Paystack transaction status using its reference.
#     """
#     secret_key = current_app.config.get('PAYSTACK_SECRET_KEY')
#     if not secret_key:
#         current_app.logger.error("Paystack secret key is not configured for verify_transaction.")
#         return {'status': False, 'message': 'Payment system not configured.'}
#     Paystack.secret_key = secret_key

#     try:
#         response_data = PaystackTransaction.verify(reference=reference)
#         if response_data.get('status') == 'success':
#             return {'status': True, 'data': response_data, 'message': response_data.get('gateway_response', 'Verification successful')}
#         else:
#             error_message = response_data.get('gateway_response', 'Verification failed or transaction not successful.')
#             current_app.logger.warning(f"Paystack verify warning/error: {error_message} - Data: {response_data}")
#             return {'status': False, 'message': f"Paystack: {error_message}", 'data': response_data}
#     except PaystackAPIError as e:
#         current_app.logger.error(f"Paystack API Error during verification: {e.strerror if hasattr(e, 'strerror') else str(e)}")
#         error_detail = e.strerror if hasattr(e, 'strerror') else str(e)
#         return {'status': False, 'message': f"Paystack Error: {error_detail}", 'data': e.data if hasattr(e, 'data') else None}
#     except Exception as e:
#         current_app.logger.error(f"Unexpected error during Paystack verification: {e}", exc_info=True)
#         return {'status': False, 'message': f"An unexpected payment error occurred: {str(e)}"}

pass # Keep file from being empty if all is commented
