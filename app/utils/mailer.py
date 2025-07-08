from flask_mail import Message
from app import mail
from flask import current_app

def send_mail(subject, recipients, body):
    msg = Message(subject, sender=current_app.config['MAIL_USERNAME'], recipients=recipients)
    msg.body = body
    mail.send(msg)
