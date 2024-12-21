from helpers.jwt import generateBearerToken
from ..db import execute, fetchOne
from flask_bcrypt import Bcrypt
from random import randint
from flask_mail import Mail, Message
from datetime import datetime, timedelta

bcrypt = Bcrypt()
mail = Mail()

def check_user(email):
    user = fetchOne("SELECT * FROM user WHERE email = '" + str(email) + "'")
    if user:
        return user
    else:
        return False
    

def registerUserByEmail(parms):
    if check_user(parms['email']):
        return {
            "error": True,
            "message": "User with this email already exist! Please try with another email"
        }

    # check password
    if not parms['password'] == parms['confirm_password']:
        return {
            "error": True,
            "message": "Password doesnot match!"
        }

    # create user
    hashedPassword = bcrypt.generate_password_hash(parms['password']).decode('utf-8')
    execute("INSERT INTO user (name, email, password, token_balance, status) VALUES ('" + str(parms['name']) + "', '" + str(parms['email']) + "', '" + hashedPassword + "', 100, 'pending')")

    user = fetchOne("SELECT * FROM user WHERE email = '" + str(parms['email']) + "'")

    # create level entry
    # execute("INSERT INTO level (user_id, level) VALUES ('" + str(user['user_id']) + "', 0)")

    # generate otp
    otp = randint(111111, 999999)

    # save otp
    expires = datetime.now() + timedelta(minutes=15)
    execute("INSERT INTO otp (user_id, otp, expires_at) VALUES ('" + str(user['user_id']) + "', '" + str(otp) + "', '" + str(expires) + "')")
    
    # mail otp to user
    msg = Message(subject="OTP for registration", sender='aiinterf@gmail.com', recipients=[parms['email']])
    msg.body = "Your OTP for registration is " + str(otp) + '. This OTP will expire in 15 minutes.'
    mail.send(msg)

    return {
        "error": False,
        "message": "OTP has been sent to your email! Validate within 15 minutes."
    }

def verifyOTPBYUserEmail(body):
    user = check_user(body['email'])
    if not user:
        return {
            "error": True,
            "message": "Invalid email"
        }
    
    otp = fetchOne("SELECT * FROM otp WHERE user_id = '" + str(user['user_id']) + "'")
    if not otp:
        return {
            "error": True,
            "message": "Invalid OTP"
        }
    if not int(otp['otp']) == int(body['otp']):
        return {
            "error": True,
            "message": "Invalid OTP"
        }
    
    if datetime.now() > otp['expires_at']:
        return {
            "error": True,
            "message": "OTP has been expired"
        }

    execute("UPDATE user SET email_verified_at = NOW() WHERE user_id = '" + str(user['user_id']) + "'")
    execute("DELETE FROM otp WHERE user_id = '" + str(user['user_id']) + "'")

    return {
        "error": False,
        "user": user
    }


def resetPasswordOTP(email):
    user = check_user(email)

    if not user:
        return {
            "error": True,
            "message": "Invalid email"
        }
    
    # delete old otps
    execute("DELETE FROM otp WHERE user_id = '" + str(user['user_id']) + "'")

    # generate otp
    otp = randint(111111, 999999)
    expires = datetime.now() + timedelta(minutes=15)
    execute("INSERT INTO otp (user_id, otp, expires_at) VALUES ('" + str(user['user_id']) + "', '" + str(otp) + "', '" + str(expires) + "')")

    # mail otp to user
    msg = Message(subject="OTP for Password reset", sender='aiinterf@gmail.com', recipients=[email])
    msg.body = "Your OTP for password reset is " + str(otp) + '. This OTP will expire in 15 minutes.'
    mail.send(msg)

    return {
        "error": False,
        "message": "OTP has been sent to your email! Validate within 15 minutes."
    }


def registerOrLoginUsingProvider(body):

    # check provider
    if(body['provider'] == 'github'):
        user = check_user(body['email'])
    else:
        if not body['email']:
            user = fetchOne("SELECT * FROM user WHERE apple_identifier = '" + str(body['apple_identifier']) + "'")
        else:
            user = check_user(body['email'])

    if(user):
        if(body['provider'] == 'apple'):
            execute("UPDATE user SET apple_identifier = '" + str(body['apple_identifier']) + "' WHERE user_id = '" + str(user['user_id']) + "'")
        token = generateBearerToken(user)
        return {'access_token': token}, 200
    
    # register user
    execute("INSERT INTO user (name, email, password, token_balance, status, email_verified_at, apple_identifier) VALUES ('" + str(body['name']) + "', '" + str(body['email']) + "', '', 100, 'pending', NOW(),'" + str(body['apple_identifier']) + "')")

    # get this user
    user = fetchOne("SELECT * FROM user WHERE email = '" + str(body['email']) + "'")

    token = generateBearerToken(user)

    return {'access_token': token}, 200
