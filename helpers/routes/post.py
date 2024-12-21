from flask import request, Blueprint

from helpers.services.post import commentPostById, createManualImagePost, createManualTextPost, createManualVideoPost, deletePostById, getAllPost, getPostByUserId, likePostById, createPostByGenerateText, createPostByGenerateImage, reportPostById, trophyPostById
from ..jwt import authGuard

post = Blueprint('post', __name__,)


@post.route('/generate/feed/post', methods=['POST'])
def createPostThroughGenerate():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    response = createPostByGenerateText(body, payload['user_id'])
    return response
@post.route('/posts', methods=['GET'])
def getAllFeeds():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    userId = request.args.get('user_id') if request.args.get('user_id') else None
    if userId:
        post = getPostByUserId(int(perPage), int(page), int(userId));
    else:
        post = getAllPost(payload['user_id'], int(perPage), int(page));
    return post;


@post.route('/me/posts', methods=['GET'])
def getCurrentUserPost():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    perPage = request.args.get('perPage') if request.args.get('perPage') else 20
    page = request.args.get('page') if request.args.get('page') else 1
    post = getPostByUserId(int(perPage), int(page), payload['user_id']);
    return post


@post.route('/posts/like/<int:post_id>', methods=['POST'])
def likePost(post_id):
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    response = likePostById(payload['user_id'], post_id)
    return {
        'status': response
    }

@post.route('/posts/trophy/<int:post_id>', methods=['POST'])
def trophyPost(post_id):
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    response = trophyPostById(payload['user_id'], post_id)
    return {
        'status': response
    }


@post.route('/posts/comment', methods=['POST'])
def commentPost():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    body = request.get_json()
    response = commentPostById(payload['user_id'], body['id'], body['comment'])
    return response


@post.route('/generate/image/post', methods=['POST'])
def createPostThroughImageGenerate():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    response = createPostByGenerateImage(body, payload['user_id'])
    return response


@post.route('/posts/text', methods=['POST'])
def create_text_post():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    response = createManualTextPost(body, payload['user_id'])
    return {
        "response": response
    }

@post.route('/posts/image', methods=['POST'])
def create_image_post():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    response = createManualImagePost(body, payload['user_id'])
    return {
        "response": response
    }

@post.route('/posts/video', methods=['POST'])
def create_video_post():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    response = createManualVideoPost(body, payload['user_id'])
    return {
        "response": response
    }

@post.route('/posts', methods=['DELETE'])
def deletePost():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    postId = request.args.get('postId')
    payload = authGuard(request)
    return deletePostById(payload['user_id'], postId)

@post.route('/post/report', methods=['POST'])
def reportPost():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    body = request.get_json()
    payload = authGuard(request)
    return reportPostById(payload['user_id'], body)