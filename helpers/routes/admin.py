from flask import request, Blueprint
from helpers.services.notice import createNotice, deleteNotice, editNotice, fetchAllNotices
from helpers.services.payments import getAllOrders, getAllWithdraws, rejectWithdawRequest, updateWithdawRequest
from helpers.services.prompt import createPrompt, deletePrompt, editPrompt, fetchAllPrompts
from helpers.services.report import fetchAllReports
from helpers.services.security import fetchSecurityDetail, updateSecurityDetailByAdmin
from helpers.services.user import getAllUser, updateUserAccessStatusById
from helpers.services.post import deletePostByAdmin, fetchAllPostByAdmin, getAllPost
from ..jwt import adminGuard

admin = Blueprint('admin', __name__,)

@admin.route('/users', methods=['GET'])
def getAllUsers():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    users = getAllUser(int(perPage), int(page));
    return users;

@admin.route('/block_user', methods=['POST'])
def updateUserStatus():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return updateUserAccessStatusById(body['user_id'])


@admin.route('/orders', methods=['GET'])
def getAllOrder():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    return getAllOrders(int(perPage), int(page))

@admin.route('/withdraws', methods=['GET'])
def getAllWithdraw():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    return getAllWithdraws(int(perPage), int(page))

@admin.route('/withdraws/<withdraw_id>', methods=['POST'])
def updateWithdraw(withdraw_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return updateWithdawRequest(withdraw_id, body)

@admin.route('/withdraws/reject/<int:withdraw_id>', methods=['POST'])
def rejectWithdraw(withdraw_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    return rejectWithdawRequest(withdraw_id)


# prompts
@admin.route('/prompts', methods=['GET'])
def getAllPrompt():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    return fetchAllPrompts(int(perPage), int(page))

@admin.route('/prompts', methods=['POST'])
def createPromptByAdmin():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return createPrompt(body)

@admin.route('/prompts/<prompt_id>', methods=['POST'])
def updatePromptByAdmin(prompt_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return editPrompt(prompt_id,body)

@admin.route('/prompts/<prompt_id>', methods=['DELETE'])
def deletePromptByAdmin(prompt_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    return deletePrompt(prompt_id)


# notices
@admin.route('/notices', methods=['GET'])
def get_all_notices():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    return fetchAllNotices(int(perPage), int(page))

@admin.route('/notices', methods=['POST'])
def createNoticeByAdmin():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return createNotice(body)

@admin.route('/notices/<notice_id>', methods=['POST'])
def updateNoticeByAdmin(notice_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return editNotice(notice_id,body)

@admin.route('/notices/<notice_id>', methods=['DELETE'])
def deleteNoticeByAdmin(notice_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    return deleteNotice(notice_id)

# report
@admin.route('/reports', methods=['GET'])
def fetAllReports():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    return fetchAllReports(int(perPage), int(page))

@admin.route('/feeds', methods=['GET'])
def fetchAllFeed():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    print(perPage, page)
    return fetchAllPostByAdmin(int(perPage), int(page))

@admin.route('/feeds/<feed_id>', methods=['DELETE'])
def deleteFeedByAdmin(feed_id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    return deletePostByAdmin(feed_id)


@admin.route('/security', methods=['GET'])
def getSecurityDetail():
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    return fetchSecurityDetail()

@admin.route('/security/<id>', methods=['POST'])
def updateSecurityDetail(id):
    if not adminGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json();
    return updateSecurityDetailByAdmin(id, body)