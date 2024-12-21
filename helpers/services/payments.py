import math
import os
import stripe

from helpers.db import execute, fetchAll, fetchOne

STRIPE_SECRET_KEY = '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'

def createPaymentIntent(amount, userId):
    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(userId))
    stripe.api_key = STRIPE_SECRET_KEY
    customerId = user['customer_id']
    if not customerId:
        customer = stripe.Customer.create(
            name=user['name'],
            email=user['email'],
        )
        customerId = customer['id']

        execute('UPDATE user SET customer_id = "' + customerId + '" WHERE user_id = ' + str(userId))

    intent = stripe.PaymentIntent.create(
        amount=int(amount)*100,
        currency='usd',
        customer=customerId,
        automatic_payment_methods={'enabled': True}
    )
    return {
        "intent": intent,
        "message": "success"
    }

def updatePaymentIntent(intentId, amount):
    stripe.api_key = STRIPE_SECRET_KEY
    intent = stripe.PaymentIntent.modify(
        intentId,
        amount=int(amount)*100
    )

    return {
        "intent": intent,
        "message": "success"
    }


def completePayment(body, userId):
    stripe.api_key = STRIPE_SECRET_KEY
    paymentintentId = body['paymentIntentId']
    amount = body['amount']
    paymentOption = body['paymentOption']

    qty = int(amount) * 96
    execute('INSERT INTO orders (user_id, payment_intent_id, price, payment_type, qty) VALUES (' + str(userId) + ', "' + paymentintentId + '", "' + str(amount) + '", "' + paymentOption + '", "' + str(qty) + '")')

    # update user token balance
    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(userId))
    updatedBalance = int(user['token_balance']) + int(qty)

    execute("UPDATE user SET token_balance = '"+ str(updatedBalance) +"' WHERE user_id = '"+ str(userId) +"'")

    return {
        "message": "success",
        "token_balance": updatedBalance
    }

def withdrawRequest(body, userId, email):
    name = body['name']
    bankName = body['bankName']
    routingNumber = body['routingNumber']
    accountNumber = body['accountNumber']
    amount = body['amount']

    execute("INSERT INTO withdraw (user_id, name, email, bank_name, routing_number, account_number, amount, created_at) VALUES ('"+ str(userId) +"', '"+ str(name) +"', '"+ str(email) +"','"+ str(bankName) +"', '"+ str(routingNumber) +"', '"+ str(accountNumber) +"', '"+ str(amount) +"', NOW())")

    return {
        "error": False,
        "message": "Withdraw request submitted successfully"
    }

def getAllOrders(perPage=20, page=1):
    offset = (page - 1) * perPage
    orders = fetchAll('SELECT orders.*, user.name, user.email FROM orders LEFT JOIN user ON orders.user_id = user.user_id ORDER BY orders.id DESC LIMIT '+ str(perPage) +' OFFSET ' + str(offset))

    count = fetchOne('SELECT count(*) as total FROM orders')

    response = {
        "page_number": page,
        "page_size": len(orders),
        "total_data": count['total'],
        "data": orders,
        "total_page": math.ceil(count['total'] / perPage)
    }
    return response

def getAllWithdraws(perPage=20, page=1):
    offset = (page - 1) * perPage
    withdraws = fetchAll('SELECT * FROM withdraw ORDER BY id DESC LIMIT '+ str(perPage) +' OFFSET ' + str(offset))

    count = fetchOne('SELECT count(*) as total FROM withdraw')

    response = {
        "page_number": page,
        "page_size": len(withdraws),
        "total_data": count['total'],
        "data": withdraws,
        "total_page": math.ceil(count['total'] / perPage)
    }
    return response

def updateWithdawRequest(id, body): 
    withdraw = fetchOne('SELECT * FROM withdraw WHERE id = ' + str(id))
    if not withdraw:
        return {
            "error": True,
            "message": "Withdraw request not found"
        }
    
    execute('UPDATE withdraw SET status = "Paid", sender_account ="'+ body['sender_account'] +'", sender_receipt="'+ body['sender_receipt'] +'" WHERE id = ' + str(id))

    withdraw = fetchOne('SELECT * FROM withdraw WHERE id = ' + str(id))
    return {
        "error": False,
        "message": "Withdraw request updated successfully",
        "withdraw": withdraw
    }

def rejectWithdawRequest(id):
    withdraw = fetchOne('SELECT * FROM withdraw WHERE id = ' + str(id))
    if not withdraw:
        return {
            "error": True,
            "message": "Withdraw request not found"
        }
    
    execute('UPDATE withdraw SET status = "Rejected" WHERE id = ' + str(id))

    withdraw = fetchOne('SELECT * FROM withdraw WHERE id = ' + str(id))
    return {
        "error": False,
        "message": "Withdraw request has been rejected!",
        "withdraw": withdraw
    }