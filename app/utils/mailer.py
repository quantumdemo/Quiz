from flask import render_template, current_app
from flask_mail import Message
from app import mail # Assuming mail is initialized in app's __init__
from threading import Thread

# Helper for async email sending
def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, text_body, html_body, sender=None):
    """
    Helper function to send an email.
    Can be run asynchronously.
    """
    if sender is None:
        # Use MAIL_USERNAME or a specific sender like ADMIN_EMAIL from config
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER', current_app.config['MAIL_USERNAME'])

    msg = Message(subject, sender=sender_email, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    # Get the Flask app instance correctly for the thread
    app_context = current_app._get_current_object()

    # Send email asynchronously to avoid blocking the request
    # For production, a task queue (e.g., Celery) is more robust.
    thread = Thread(target=send_async_email, args=[app_context, msg])
    thread.start()
    # To wait for thread completion (for testing or specific cases), you might use thread.join(),
    # but generally for web requests, you want it to run in the background.

def send_verification_email(user_email, verification_url):
    """
    Sends the email verification email to the user.
    """
    subject = "Verify Your Email Address"

    # Ensure email templates directory exists: app/templates/email/
    # And files: verify_email.txt, verify_email.html
    send_email(
        subject=subject,
        recipients=[user_email],
        text_body=render_template("email/verify_email.txt", verification_url=verification_url, user_email=user_email),
        html_body=render_template("email/verify_email.html", verification_url=verification_url, user_email=user_email)
    )

def send_password_reset_email(user_email, reset_url):
    """
    Sends a password reset email to the user.
    (This is for future use, but good to have in the mailer)
    """
    subject = "Reset Your Password"
    send_email(
        subject=subject,
        recipients=[user_email],
        text_body=render_template("email/reset_password.txt", reset_url=reset_url, user_email=user_email),
        html_body=render_template("email/reset_password.html", reset_url=reset_url, user_email=user_email)
    )

# It's good practice to add MAIL_DEFAULT_SENDER to config if you want a different display name or email
# than the MAIL_USERNAME used for authentication with the SMTP server.
# For example: Config.MAIL_DEFAULT_SENDER = ('Your App Name', 'noreply@example.com')
# If not set, it defaults to MAIL_USERNAME.
# I also added user_email to the template context for personalization.
