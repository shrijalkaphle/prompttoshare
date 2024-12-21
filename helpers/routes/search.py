from flask import request, Blueprint

from helpers.services.search import searchAll

from ..jwt import authGuard

search = Blueprint('search', __name__,)

@search.route('/search', methods=['GET'])
def search_all():
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    payload = authGuard(request)
    searchParams = request.args.get('query')
    response = searchAll(searchParams, payload['user_id'])
    return response