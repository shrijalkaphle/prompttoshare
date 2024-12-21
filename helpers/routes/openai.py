from flask import request, Blueprint

from helpers.services.openai import generatePostFeed, generateDalleImage, editDalleImage, getAvailablePrompt

from ..jwt import authGuard

openai = Blueprint('openai', __name__,)

@openai.route('/generate/feed', methods=['POST'])
def generateFeedText():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    body = request.get_json()
    response = generatePostFeed(payload['user_id'], body['prompt'], body['category'])
    return response

@openai.route('/generate/image', methods=['POST'])
def generateImage():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()

    response = generateDalleImage(body['prompt'])
    return response

@openai.route('/generate/edit/image', methods=['POST'])
def editImage():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()

    response = editDalleImage(body['prompt'], body['original'], body['mask'])
    return response

@openai.route('/prompts', methods=['GET'])
def getPrompts():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    response = getAvailablePrompt()
    return response