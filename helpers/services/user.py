from helpers.services.upload import uploadUserProfile
from ..db import execute, fetchAll, fetchOne
from flask_bcrypt import Bcrypt, check_password_hash


from datetime import datetime

import math

price_per_like = 0.01
price_per_trophy = 0.25

bcrypt = Bcrypt()
def getAllUser(perPage = 20, page = 1):
    offset = (page - 1) * perPage
    users = fetchAll('SELECT user.*, level.level FROM user LEFT JOIN level ON user.user_id = level.user_id ORDER BY user.user_id DESC LIMIT '+ str(perPage) +' OFFSET ' + str(offset))
    for user in users:
        del user['password']
        user['circle'] = fetchOne('SELECT count(*) AS total FROM follows WHERE follower_id = ' + str(user['user_id']))['total']
        user['reward'] = fetchOne('SELECT count(likes.id) AS total FROM likes LEFT JOIN feed ON likes.post_id = feed.id WHERE feed.user_id = ' + str(user['user_id']))['total']
        user['trophy'] = fetchOne('SELECT count(trophy.id) AS total FROM trophy LEFT JOIN feed ON trophy.post_id = feed.id WHERE feed.user_id = ' + str(user['user_id']))['total']
        
    count = fetchOne('SELECT count(*) as total FROM user')

    response = {
        "page_number": page,
        "page_size": len(users),
        "total_data": count['total'],
        "data": users,
        "total_page": math.ceil(count['total'] / perPage)
    }
    return response


def getUserById(user_id):
    user = fetchOne('SELECT user.*, level.level FROM user LEFT JOIN level ON user.user_id = level.user_id WHERE user.user_id = ' + str(user_id))
    user['circle'] = fetchOne('SELECT count(*) AS total FROM follows LEFT JOIN user ON user.user_id = follows.following_id WHERE user.status IS NULL AND follower_id = ' + str(user['user_id']))['total']
    user['reward_received'] = fetchOne('SELECT count(likes.id) AS total FROM likes LEFT JOIN feed ON likes.post_id = feed.id WHERE feed.user_id = ' + str(user_id))['total']
    user['trophy_received'] = fetchOne('SELECT count(trophy.id) AS total FROM trophy LEFT JOIN feed ON trophy.post_id = feed.id WHERE feed.user_id = ' + str(user_id))['total']
    user['reward_given'] = len(fetchAll('SELECT * FROM likes WHERE user_id = ' + str(user_id)))
    user['trophy_given'] = len(fetchAll('SELECT * FROM trophy WHERE user_id = ' + str(user_id)))
    user['generate_history'] = len(fetchAll('SELECT * FROM history WHERE user_id = ' + str(user_id)))
    user['total_price'] = (price_per_trophy*user['trophy_received']) + (price_per_like*user['reward_received'])
    user['report_count'] = len(fetchAll('SELECT * FROM report WHERE user_id = ' + str(user_id)))
    rating = fetchOne('SELECT avg(rating_value) FROM profile_rating WHERE profile_id = ' + str(user_id))['avg(rating_value)']
    user['average_rating'] = rating if rating else 0
    user['rating_count'] = len(fetchAll('SELECT * FROM profile_rating WHERE profile_id = ' + str(user_id)))
    user['role'] = 'admin' if user['user_id'] == 1 else 'user'
    del user['password']
    return user


def getUserBillingInfoById(user_id):
    bought = fetchAll('SELECT * FROM orders WHERE user_id = ' + str(user_id) + ' ORDER BY id DESC')
    withdraw = fetchAll('SELECT * FROM withdraw WHERE user_id = ' + str(user_id) + ' ORDER BY id DESC')

    return {'bought': bought, 'withdraw': withdraw}


def getUserNotifications(user_id, perPage, page):
    notifications = fetchAll('SELECT * FROM notification WHERE user_id = ' + str(user_id) + ' ORDER BY id DESC LIMIT ' + str(perPage) + ' OFFSET ' + str((page - 1) * perPage))
    total = fetchOne('SELECT count(*) as total FROM notification WHERE user_id = ' + str(user_id))
    return {
        "page_number": page,
        "page_size": len(notifications),
        "total_data": total['total'],
        "data": notifications,
        "total_page": math.ceil(total['total'] / perPage)
    }


def searchUser(search, currentUserId):
    users = fetchAll('SELECT user.*, level.level FROM user LEFT join level on user.user_id = level.user_id WHERE user.user_id NOT IN (SELECT blocked_user_id FROM blocked_user WHERE user_id = ' + str(currentUserId) + ') AND user.name LIKE "%' + search + '%"')
    return users


def updateUserPasswordById(user_id, password):
    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(user_id))
    if check_password_hash (user['password'], password):
        return {'message': 'Old password and new password cannot be same.', 'error': True}
    
    hashedPassword = bcrypt.generate_password_hash(password).decode('utf-8')
    execute('UPDATE user SET password = "' + hashedPassword + '" WHERE user_id = ' + str(user_id))
    
    return {'message': 'Password Changed'}


def updateUserDetailById(user_id, body):
    name = body['name']
    email = body['email']
    execute('UPDATE user SET name = "' + name + '", email = "' + email + '" WHERE user_id = ' + str(user_id))
    user = getUserById(user_id)
    return {'message': 'Detail Changed', 'user': user}

def updateUserProfileById(user_id, file):
    profile = uploadUserProfile(file)
    execute('UPDATE user SET profile = "' + profile + '" WHERE user_id = ' + str(user_id))
    user = getUserById(user_id)
    return {'message': 'Detail Changed', 'user': user}


def getCircleUsersByUserId(userId):
    followed = fetchAll('SELECT * FROM follows LEFT JOIN user ON user.user_id = follows.following_id WHERE user.status IS NULL AND follower_id = ' + str(userId))
    circle = []
    for f in followed:
        user = getUserById(f['following_id'])
        circle.append(user)

    return circle

def reportProblemByUserId(body, userId):
    execute('INSERT INTO report (user_id, title, message, created_at) VALUES ("'+ str(userId) +'","'+ body['title'] +'", "'+ body['message'] +'", NOW())')

    return {
        'message': 'Report Submitted',
        'error': False
    }

def getIfUserFollowed(currentUserId, userId):
    follow = fetchOne('SELECT * FROM follows WHERE follower_id = ' + str(currentUserId) + ' AND following_id = ' + str(userId))
    if follow:
        return True
    return False


def updateFollowingStatusByUserId(currentUserId, userId):
    follow = fetchOne('SELECT * FROM follows WHERE follower_id = ' + str(currentUserId) + ' AND following_id = ' + str(userId))
    if follow:
        execute('DELETE FROM follows WHERE follower_id = ' + str(currentUserId) + ' AND following_id = ' + str(userId))
    else:
        execute('INSERT INTO follows (follower_id, following_id, created_at) VALUES ("'+ str(currentUserId) +'","'+ str(userId) +'", NOW())')
    return True

def rateUserById(body, userId):

    # check if previous rating exists
    rating = fetchOne('SELECT * FROM profile_rating WHERE user_id = ' + str(userId) +' AND profile_id = ' + str(body['profileId']))
    if rating:
        execute('UPDATE profile_rating SET rating_value = "'+ str(body['rating']) +'" WHERE id = ' + str(rating['id']))
    else:
        execute('INSERT INTO profile_rating (user_id, profile_id, rating_value) VALUES ("'+ str(userId) +'","'+ str(body['profileId']) +'","'+ str(body['rating']) +'")')
    

    user = getUserById(body['profileId'])
    followed = getIfUserFollowed(userId, user['user_id'])
    user['isFollowed'] = followed
    return {
        'message': 'Rating Submitted',
        'error': False,
        'user': user
    }


def deleteUserProfile(userId):
    execute('UPDATE user SET status = "delete" WHERE user_id = ' + str(userId))

    # hide all user posts
    execute('UPDATE feed SET deleted_at = NOW() WHERE user_id = ' + str(userId))
    execute('UPDATE comment SET deleted_at = NOW() WHERE user_id = ' + str(userId))
    return {
        "message": "Profile Deleted"
    }

def getBlockedUsersByUserId(userId):
    blockedList = fetchAll('SELECT blocked_user.id, user.user_id, user.name, user.profile FROM blocked_user LEFT JOIN user ON user.user_id = blocked_user.blocked_user_id WHERE blocked_user.user_id = ' + str(userId))
    return {
        "blocked": blockedList
    }


def blockUserById(currentUserId, blockUserId):
    status = 'blocked'

    # check if user exists
    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(blockUserId))
    if not user:
        return {
            'message': 'User does not exist',
            'error': True
        }

    blocked = fetchOne('SELECT * FROM blocked_user WHERE user_id = ' + str(currentUserId) + ' AND blocked_user_id = ' + str(blockUserId))
    if blocked:
        execute('DELETE FROM blocked_user WHERE user_id = ' + str(currentUserId) + ' AND blocked_user_id = ' + str(blockUserId))
        status = 'unblocked'
    else:
        execute('INSERT INTO blocked_user (user_id, blocked_user_id) VALUES ("'+ str(currentUserId) +'","'+ str(blockUserId) +'")')
        # remove from circle if exists
        # Remove user from circle if exists
        execute('DELETE FROM follows WHERE follower_id = "'+ str(blockUserId) +'" AND following_id = "'+ str(blockUserId) +'"')
    
    return {
        'message': f'User has been {status}.',
        'error': False
    }

def updateUserAccessStatusById(userId):
    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(userId))
    if not user:
        return {
            'message': 'User does not exist',
            'error': True
        }
    
    status = 0 if user['is_blocked'] else 1
    message = 'User has been Unblocked.' if status == 0 else 'User has been Blocked.'
    
    execute('UPDATE user SET is_blocked = "'+ str(status) +'" WHERE user_id = ' + str(userId))

    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(userId))
    return {
        'message': message,
        'error': False,
        'user': user
    }