import jwt

SECRET_KEY = 'dUDjDdjBH2Xy4CpXwbILJX2MoB0BXzz6XfJmsKHqLV8'
def generateBearerToken(user):
    payload = {
        "user_id": user['user_id'],
        "email": user['email'],
        "name": user['name'],
        "role": "admin" if user['user_id'] ==1 else "user"
    };

    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    return token


def authGuard(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    token = auth_header.split(' ')[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    if(payload['role'] == 'user' or payload['role'] == 'admin'):
        return payload
    return False

def adminGuard(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False
    token = auth_header.split(' ')[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    if(payload['role'] == 'admin'):
        return payload
    return False