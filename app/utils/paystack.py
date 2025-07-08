import requests
import os

PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')
HEADERS = {
    'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
    'Content-Type': 'application/json'
}

PAYSTACK_INIT_URL = 'https://api.paystack.co/transaction/initialize'
PAYSTACK_VERIFY_URL = 'https://api.paystack.co/transaction/verify/'

def initialize_transaction(email, amount, reference):
    data = {
        'email': email,
        'amount': int(amount * 100),
        'reference': reference
    }
    response = requests.post(PAYSTACK_INIT_URL, json=data, headers=HEADERS)
    return response.json()

def verify_transaction(reference):
    url = PAYSTACK_VERIFY_URL + reference
    response = requests.get(url, headers=HEADERS)
    return response.json()
