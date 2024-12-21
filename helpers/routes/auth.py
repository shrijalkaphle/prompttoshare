from flask import request, Blueprint

from ..jwt import  generateBearerToken, authGuard
from ..services.auth import check_user, registerUserByEmail, resetPasswordOTP, verifyOTPBYUserEmail, registerOrLoginUsingProvider
from flask_bcrypt import check_password_hash

from ..services.user import getIfUserFollowed, getUserById, updateFollowingStatusByUserId, updateUserDetailById, updateUserPasswordById, updateUserProfileById

auth = Blueprint('auth', __name__,)

@auth.route('/login', methods=['POST'])
def login():
    body = request.get_json()
    user = check_user(body['email'])
    if not user:
        return {'message': 'Invalid email'}, 401
    
    if not check_password_hash(user['password'], body['password']):
        return {'message': 'Invalid password'}, 401
    
    if not user['email_verified_at']:
        return {'message': 'Please verify your email'}, 401

    if user['status'] == 'delete':
        return {'message': 'Your account has been deleted'}, 401
    
    token = generateBearerToken(user)

    return {'access_token': token}, 200


@auth.route('/register', methods=['POST'])
def register():
    body = request.get_json()
    return registerUserByEmail(body)

@auth.route('/me', methods=['GET'])
def me():
    payload = authGuard(request)
    if not payload:
        return {'message': 'Unauthorized Access'}, 401
    
    user = getUserById(payload['user_id'])
    return user

@auth.route('/update-password', methods=['POST'])
def updatePassword():
    payload = authGuard(request)
    if not payload:
        return {'message': 'Unauthorized Access'}, 401
    
    body = request.get_json()
    return updateUserPasswordById(payload['user_id'], body['password'])


@auth.route('/update-detail', methods=['POST'])
def updateDetail():
    payload = authGuard(request)
    if not payload:
        return {'message': 'Unauthorized Access'}, 401
    
    body = request.get_json()
    return updateUserDetailById(payload['user_id'], body)

@auth.route('/update-profile', methods=['POST'])
def updateProfilePic():
    payload = authGuard(request)
    if not payload:
        return {'message': 'Unauthorized Access'}, 401
    
    profile = request.files.get('profile')
    return updateUserProfileById(payload['user_id'], profile)


@auth.route('/verify-register', methods=['POST'])
def verifyOTP():
    body = request.get_json()
    response = verifyOTPBYUserEmail(body)
    if response['error']:
        return response, 401
    token = generateBearerToken(response['user'])
    return {'access_token': token}, 200

@auth.route('/verify-email', methods=['POST'])
def verifyEmail():
    body = request.get_json()
    return resetPasswordOTP(body['email'])


@auth.route('/verify-password-reset', methods=['POST'])
def verifyEmailForPasswordReset():
    body = request.get_json()
    response = verifyOTPBYUserEmail(body)
    if response['error']:
        return response, 401
    
    return {
        "error": False,
        "message": "Continue to reset password",
        "user": response['user']
    }

@auth.route('/update-forgot-password', methods=['POST'])
def updateForgotPasswordFromOTP():
    body = request.get_json()
    print(body)
    return updateUserPasswordById(body['user_id'], body['password'])

@auth.route('/update-following', methods=['POST'])
def updateFollowingStatus():
    payload = authGuard(request)
    if not payload:
        return {'message': 'Unauthorized Access'}, 401
    
    body = request.get_json()
    response = updateFollowingStatusByUserId(payload['user_id'], body['user_id'])
    if(response):
        user = getUserById(body['user_id'])
        user['isFollowed'] = getIfUserFollowed(payload['user_id'], body['user_id'])
        return user
    
    return {
        "error" : True,
        "message" : "Something went wrong"
    }

@auth.route('/provider-login', methods=['POST'])
def loginWithProvider():
    body = request.get_json()
    return registerOrLoginUsingProvider(body)