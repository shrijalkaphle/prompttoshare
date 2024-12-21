from flask import request, Blueprint
from helpers.services.user import blockUserById, deleteUserProfile, getBlockedUsersByUserId, getCircleUsersByUserId, getUserById, getUserBillingInfoById, getUserNotifications, rateUserById, reportProblemByUserId, getIfUserFollowed
from helpers.jwt import authGuard

user = Blueprint('user', __name__,)

@user.route('/users/<user_id>', methods=['GET'])
def getUserByUserId(user_id):
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    user = getUserById(user_id);
    payload = authGuard(request)

    # get if user is followed
    followed = getIfUserFollowed(payload['user_id'], user_id)
    user['isFollowed'] = followed
    return user;

@user.route('/me/billing', methods=['GET'])
def getUserBillingDetail():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    payload = authGuard(request)
    billing = getUserBillingInfoById(payload['user_id']);
    return billing

@user.route('/me/notifications', methods=['GET'])
def getNotification():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    payload = authGuard(request)
    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    notifications = getUserNotifications(payload['user_id'], int(perPage), int(page));
    return notifications

@user.route('me/circles', methods=['GET'])
def getCircleUsers():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    payload = authGuard(request)
    # return payload
    circles = getCircleUsersByUserId(payload['user_id'])
    return circles

@user.route('me/report-problem', methods=['POST'])
def reportProblem():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    body = request.get_json()
    payload = authGuard(request)
    return reportProblemByUserId(body, payload['user_id'])

@user.route('user/rating', methods=['POST'])
def rateUser():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    body = request.get_json()
    payload = authGuard(request)
    return rateUserById(body, payload['user_id'])

@user.route('me/delete', methods=['POST'])
def deleteProfile():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    payload = authGuard(request)
    return deleteUserProfile(payload['user_id'])

@user.route('me/blocked_users', methods=['GET'])
def getBlockedUser():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    payload = authGuard(request)
    return getBlockedUsersByUserId(payload['user_id'])

@user.route('user/block', methods=['POST'])
def blockUser():
    if not authGuard(request):
        return {'error': 'Unauthorized Access'};

    body = request.get_json()
    payload = authGuard(request)
    return blockUserById(payload['user_id'], body['blockedUserId'])