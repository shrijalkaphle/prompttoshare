import math
import io
import os
import re
import boto3
import tempfile
from datetime import datetime
import requests
from PIL import Image
import unidecode
from werkzeug.utils import secure_filename

from helpers.level import calculateLevel
from ..db import fetchAll, fetchOne, execute

BUCKET_NAME = 'ai-interf-social'
AWS_ACCESS_KEY_ID = '#########################'
AWS_SECRET_ACCESS_KEY = $SECRET_ACCESS_KEY

def fetchAllPostByAdmin(perPage = 20, page = 1):
    offset = (page - 1) * perPage

    feeds = fetchAll('SELECT feed.* FROM feed WHERE deleted_at IS NULL ORDER BY id DESC LIMIT '+ str(perPage) +' OFFSET ' + str(offset))
    for feed in feeds:
        feed['user'] = fetchOne('SELECT * FROM user WHERE user_id = ' + str(feed['user_id']))
        feed['comment'] = fetchAll('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE deleted_at IS NULL AND post_id = ' + str(feed['id']))
        feed['like'] = fetchAll('SELECT likes.*, user.name, user.profile FROM likes JOIN user ON likes.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['trophy'] = fetchAll('SELECT trophy.*, user.name, user.profile FROM trophy JOIN user ON trophy.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        
        del feed['user_id']
        del feed['user']['password']

    count = fetchOne('SELECT count(*) as total FROM feed WHERE deleted_at IS NULL')

    response = {
        "page_number": page,
        "page_size": len(feeds),
        "total_data": count['total'],
        "data": feeds,
        "total_page": math.ceil(count['total'] / perPage)
    }
    return response


def deletePostByAdmin(postId):
    execute('DELETE FROM feed WHERE id = ' + str(postId))
    execute('DELETE FROM comment WHERE post_id = ' + str(postId))
    execute('DELETE FROM likes WHERE post_id = ' + str(postId))
    execute('DELETE FROM trophy WHERE post_id = ' + str(postId))

    return { "error": False, "message": "Post deleted successfully" }

def getAllPost(currentUserId, perPage = 20, page = 1):
    offset = (page - 1) * perPage
    # get all blocked users

    feeds = fetchAll('SELECT feed.* FROM feed WHERE user_id NOT IN (SELECT blocked_user_id FROM blocked_user WHERE user_id = ' + str(currentUserId) + ') AND feed.deleted_at IS NULL AND feed.status IS NULL ORDER BY id DESC LIMIT '+ str(perPage) +' OFFSET ' + str(offset))
    for feed in feeds:
        feed['user'] = fetchOne('SELECT * FROM user WHERE user_id = ' + str(feed['user_id']))
        feed['comment'] = fetchAll('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE deleted_at IS NULL AND post_id = ' + str(feed['id']))
        feed['like'] = fetchAll('SELECT likes.*, user.name, user.profile FROM likes JOIN user ON likes.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['trophy'] = fetchAll('SELECT trophy.*, user.name, user.profile FROM trophy JOIN user ON trophy.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        
        del feed['user_id']
        del feed['user']['password']

    count = fetchOne('SELECT count(*) as total FROM feed WHERE user_id NOT IN (SELECT blocked_user_id FROM blocked_user WHERE user_id = ' + str(currentUserId) + ') AND feed.deleted_at IS NULL')

    response = {
        "page_number": page,
        "page_size": len(feeds),
        "total_data": count['total'],
        "data": feeds,
        "total_page": math.ceil(count['total'] / perPage)
    }
    return response


def getPostById(post_id):
    feed = fetchOne('SELECT * FROM feed WHERE id = '+ str(post_id))
    feed['user'] = fetchOne('SELECT * FROM user WHERE user_id = ' + str(feed['user_id']))
    feed['comment'] = fetchAll('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE post_id = ' + str(post_id))
    feed['like'] = fetchAll('SELECT likes.*, user.name, user.profile FROM likes JOIN user ON likes.user_id = user.user_id WHERE post_id = ' + str(post_id))
    feed['trophy'] = fetchAll('SELECT trophy.*, user.name, user.profile FROM trophy JOIN user ON trophy.user_id = user.user_id WHERE post_id = ' + str(post_id))

    return feed


def getPostByUserId(perPage, page, user_id):
    offset = (page - 1) * perPage
    feeds = fetchAll('SELECT * FROM feed WHERE user_id = ' + str(user_id) + ' ORDER BY id DESC LIMIT '+ str(perPage) +' OFFSET ' + str(offset))
    for feed in feeds:
        feed['user'] = fetchOne('SELECT * FROM user WHERE user_id = ' + str(feed['user_id']))
        feed['comment'] = fetchAll('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['like'] = fetchAll('SELECT likes.*, user.name, user.profile FROM likes JOIN user ON likes.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['trophy'] = fetchAll('SELECT trophy.*, user.name, user.profile FROM trophy JOIN user ON trophy.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
    
    count = fetchOne('SELECT count(*) as total FROM feed WHERE user_id = ' + str(user_id))
    response = {
        "page_number": page,
        "page_size": len(feeds),
        "total_data": count['total'],
        "data": feeds,
        "total_page": math.ceil(count['total'] / perPage)
    }
    return response

def postsToShow(page = 1):
    feeds = fetchAll('SELECT * FROM feed')
    for feed in feeds:
        feed['user'] = fetchOne('SELECT * FROM user WHERE user_id = ' + str(feed['user_id']))
        feed['comment'] = fetchAll('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['like'] = fetchAll('SELECT likes.*, user.name, user.profile FROM likes JOIN user ON likes.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['trophy'] = fetchAll('SELECT trophy.*, user.name, user.profile FROM trophy JOIN user ON trophy.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
    
    sorted_by_latest = sorted(feeds, key=lambda x: x['created_at'], reverse=True)
    sorted_by_highest_awarded = sorted(feeds, key=lambda x: (-x['like_count'], -x['trophy_count']))

    latest_2_posts = sorted_by_latest[0:2]
    highest_awarded_3_posts = sorted_by_highest_awarded[0:3]
    latest_5_posts = sorted_by_latest[2:7]
    highest_awarded_7_posts = sorted_by_highest_awarded[3:10]
    latest_15_posts = sorted_by_latest[8:23]

    filtered_posts = latest_2_posts + highest_awarded_3_posts + latest_5_posts + highest_awarded_7_posts + latest_15_posts


def likePostById(user_id, post_id):

    like = fetchOne('SELECT * FROM likes WHERE user_id = ' + str(user_id) + ' AND post_id = ' + str(post_id))
    if not like:
        user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(user_id))
        if user['token_balance'] == 0:
            return {
                "message": "Insufficient token balance",
            }
        execute('INSERT INTO likes (user_id, post_id) VALUES (' + str(user_id) + ',' + str(post_id) + ')')
        execute('UPDATE user SET token_balance = token_balance - 1 WHERE user_id = '+ str(post_id) + '')
        return {
            "message": "You have liked this post",
        }
    else:
        return {
            "message": "You have already liked this post",
        }
def trophyPostById(user_id, post_id):
    trophy = fetchOne('SELECT * FROM trophy WHERE user_id = ' + str(user_id) + ' AND post_id = ' + str(post_id))

    if trophy:
        return {
            "message": "You have already awarded trophy to this post",
        }
    
    user = fetchOne('SELECT * FROM user WHERE user_id = ' + str(user_id))
    if user['token_balance'] < 25:
        return {
            "message": "Insufficient token balance",
        }
    execute('UPDATE user SET token_balance = token_balance - 25 WHERE user_id = '+ str(user_id) +'')
    execute('INSERT INTO trophy (user_id, post_id) VALUES ('+ str(user_id) + ',' + str(post_id) +')')
    calculateLevel()

    # get user level
    level = fetchOne('SELECT * FROM level WHERE user_id = ' + str(user_id))['level']
    return {
        "message": "You have awarded this post",
        "level": level
    } 
def commentPostById(user_id, post_id, comment):
    execute('INSERT INTO comment (user_id, post_id, text) VALUES ('+ str(user_id) + ',' + str(post_id) +',"' + str(comment) + '")')
    # 'INSERT INTO comment (text, user_id, post_id) VALUES (%s, %s, %s)', (comment, user_id, post_id)
    comment = fetchAll('SELECT comment.*, user.name, user.profile FROM comment LEFT JOIN user ON comment.user_id = user.user_id WHERE post_id = ' + str(post_id))
    return {
        "status": True,
        "message": "You have commented on this post",
        "comment": comment
    }

def createPostByGenerateText(body, user_id):
    if(not body['title'] or not body['chunk'] or not body['category']):
        return {
            "status": False,
            "message": "All fields are required"
        }
    try:
        text = unidecode.unidecode(body['title']).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        query = 'INSERT INTO feed (title, slug, chunk, user_id, category, created_at) VALUES ("'+ body['title'] +'","'+ slug +'","'+ body['chunk'] +'","'+ str(user_id) +'", "'+ body['category'] +'", NOW())'
        execute(query)
        return {
            "status": True,
            "message": "Post created successfully"
        }
    except:
        return {
            "status": False,
            "message": "Something went wrong"
        }

def searchPost(search, currentUserId):
    query = 'SELECT feed.* FROM feed LEFT JOIN user ON feed.user_id = user.user_id WHERE feed.user_id NOT IN (SELECT blocked_user_id FROM blocked_user WHERE user_id = ' + str(currentUserId) + ') AND (feed.title LIKE "%' + search + '%" OR user.name LIKE "%' + search + '%") ORDER BY feed.id DESC LIMIT 20'
    feeds = fetchAll(query)
    for feed in feeds:
        feed['user'] = fetchOne('SELECT * FROM user WHERE user_id = ' + str(feed['user_id']))
        feed['comment'] = fetchAll('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['like'] = fetchAll('SELECT likes.*, user.name, user.profile FROM likes JOIN user ON likes.user_id = user.user_id WHERE post_id = ' + str(feed['id']))
        feed['trophy'] = fetchAll('SELECT trophy.*, user.name, user.profile FROM trophy JOIN user ON trophy.user_id = user.user_id WHERE post_id = ' + str(feed['id']))

    return feeds


def createPostByGenerateImage(body, user_id):
    image_url = body['image_url']
    category = body['category']
    prompt = body['prompt']
    chunk = ''

    if image_url:
        response = requests.get(image_url)
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            max_size_kb = 50  # Target size in KB
            quality = 95  # Initial quality
            buffer = io.BytesIO()
            while True:
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality)
                if buffer.getbuffer().nbytes < max_size_kb * 1024 or quality <= 10:
                    break
                quality -= 5
            
            unique_filename = f"generated-{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(buffer.getvalue())

            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            image_filename = secure_filename(unique_filename)

            s3.upload_file(temp_file.name, BUCKET_NAME, image_filename)
            # Get the S3 URL for the uploaded image file
            image_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{image_filename}"
            file_path = image_s3_url
            os.remove(temp_file.name)

        else:
            return { "status": False, "message": "Failed to download image" }
    else:
        file_path = ""

    try:
        slug = re.sub(r'[\W_]+', '_', prompt)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        execute('INSERT INTO feed (file, title, user_id, chunk, category, created_at, slug) VALUES ("'+ file_path +'", "'+ prompt +'", "'+ str(user_id) +'","'+ chunk +'", "'+ category +'", NOW(), "'+ slug +'")')
        return { "status": True, "message": "Post created successfully" }
    except:
        return { "status": False, "message": "Something went wrong" }


def createManualTextPost(body, user_id):
    try:
        category = 'extra'
        text = unidecode.unidecode(body['prompt']).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        execute('INSERT INTO feed (title, slug, chunk, user_id, category, created_at) VALUES ("'+ body['prompt'] +'","'+ slug +'","'+ body['chunk'] +'","'+ str(user_id) +'", "'+ category +'", NOW())')
        return { "status": True, "message": "Post created successfully", "body" : body }
    except:
        return { "status": False, "message": "Something went wrong" }


def createManualImagePost(body, user_id):
    try:
        category = 'extra'
        text = unidecode.unidecode(body['prompt']).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        execute('INSERT INTO feed (title, slug, user_id, category, file, tool, status, token, created_at) VALUES ("'+ body['prompt'] +'","'+ slug +'","'+ str(user_id) +'", "'+ category +'", "'+ body['file'] +'", "'+ body['imageProvider'] +'", "processing", "'+ body['token'] +'", NOW())')
        return { "status": True, "message": "Post created successfully", "body" : body }
    except:
        return { "status": False, "message": "Something went wrong" }

def createManualVideoPost(body, user_id):
    try:
        category = 'extra'
        text = unidecode.unidecode(body['prompt']).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        execute('INSERT INTO feed (title, slug, file, user_id, category, status, token, created_at) VALUES ("'+ body['prompt'] +'", "'+ slug +'","'+ body['file'] +'","'+ str(user_id) +'", "'+ category +'", "processing", "'+ body['token'] +'", NOW())')
        return { "status": True, "message": "Post created successfully", "body" : body }
    except:
        return { "status": False, "message": "Something went wrong" }


def deletePostById(user_id, post_id):
    post = fetchOne('SELECT * FROM feed WHERE id = ' + str(post_id) + ' AND user_id = ' + str(user_id))
    if not post:
        return { "error": True, "message": "Permission denied!" }
    
    try:
        execute('DELETE FROM feed WHERE id = ' + str(post_id))
        execute('DELETE FROM comment WHERE post_id = ' + str(post_id))
        execute('DELETE FROM likes WHERE post_id = ' + str(post_id))
        execute('DELETE FROM trophy WHERE post_id = ' + str(post_id))

        return { "error": False, "message": "Post deleted successfully" }
    except:
        return { "error": True, "message": "Error while deleting post" }

def reportPostById(userId, body):
    
    postId = body['postId']
    reason = body['reason']

    post = fetchOne('SELECT * FROM feed WHERE id = ' + str(postId))
    if not post:
        return { "error": True, "message": "Post not found!" }

    try: 
        execute('INSERT INTO report_post (user_id, post_id, reason, created_at) VALUES ("'+ str(userId) +'","'+ str(postId) +'","'+ reason +'", NOW())')

        return {
            'message': 'Report Submitted',
            'error': False
        }
    except:
        return { "error": True, "message": "Error while reporting post" }