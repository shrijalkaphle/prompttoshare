from flask import request, Blueprint

from helpers.services.payments import createPaymentIntent, updatePaymentIntent, completePayment, withdrawRequest
from ..jwt import authGuard

payments = Blueprint('payments', __name__,)

@payments.route('/create_payment_intent', methods=['POST'])
def create_payment_intent():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    return createPaymentIntent(body['amount'],payload['user_id'])

@payments.route('/update_payment_intent', methods=['POST'])
def update_payment_intent():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    return updatePaymentIntent(body['payment_intent_id'], body['amount'])

@payments.route('/complete_payment', methods=['POST'])
def complete_payment():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    return completePayment(body, payload['user_id'])


@payments.route('/withdraw-request', methods=['POST'])
def withdraw_request():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    return withdrawRequest(body, payload['user_id'],payload['email'])