import os
import re
import openai
import time
import json
import base64
import boto3
import botocore
import random
import requests
import sseclient
from flask import Flask, redirect, render_template, request, url_for, session, jsonify, flash, Response
from flask_oauthlib.client import OAuth
from markupsafe import Markup
from werkzeug.utils import secure_filename
from openai import Completion

from flask_bcrypt import Bcrypt, check_password_hash


from flask_wtf.csrf import CSRFProtect


from flask_mysqldb import MySQL
from flask_mail import Mail, Message
import MySQLdb.cursors
import re
import uuid

app = Flask(__name__, static_url_path='/static')
bcrypt = Bcrypt(app)

app.secret_key = 'I%uI*&LuV4yX92ve'

# Facebook App Configurations
FB_APP_ID = '861161571799626'
FB_APP_SECRET = '6e00b8fcf9a25456dfc7ae77d8c161cb' 
FB_REDIRECT_URI = 'http://localhost:5000/facebook/callback'

oauth = OAuth(app)

# Configuration for Google Sign-In
google = oauth.remote_app(
    'google',
    consumer_key='64551788821-eijgv2odigrnkaffk0fd9the0f9s7mn2.apps.googleusercontent.com',  # Replace with your Google Client ID
    consumer_secret='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',  # Replace with your Google Client Secret
    request_token_params={
        'scope': 'email profile',
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)


csrf = CSRFProtect(app)
csrf.init_app(app)


# UPLOAD_FOLDER = 'static/upload_file'
# UPLOAD_PROFILE = 'static/upload_profile'

 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'counselai'
# app.config['MYSQL_UNIX_SOCKET'] = '/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock'

# app.config['MYSQL_HOST'] = 'us-cdbr-east-06.cleardb.net'
# app.config['MYSQL_USER'] = 'b57d02d193bc19'
# app.config['MYSQL_PASSWORD'] = 'a3f1503e'
# app.config['MYSQL_DB'] = 'heroku_7e298305dcadd8d'
mysql = MySQL(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USE_SSL'] = 'True'
app.config['MAIL_USE_TSL'] = 'False'
app.config['MAIL_USERNAME'] = 'testing13001@gmail.com'
app.config['MAIL_PASSWORD'] = 'tolhazhrnyyowtfn'
mail = Mail(app)


# AWS S3 configuration
BUCKET_NAME = 'ai-interf-social'
AWS_ACCESS_KEY_ID = 'AKIARQFQUHJED7N5LPHF'
AWS_SECRET_ACCESS_KEY = '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'


from dotenv import load_dotenv 
load_dotenv()
openai.api_key = "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"
model_engine = 'text-davinci-003'

# Set the max number of characters per chunk
MAX_CHARS_PER_CHUNK = 500

# Set the words per minute for text streaming
WORDS_PER_MINUTE = 60

@app.route('/test')
def test():
    return render_template('test.html')






#----------Admin Page section-------
@app.route("/ai-interf-social-admin", methods=("GET", "POST"))
def admin():
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    user_id = session['user_id']

    if user_id == 1:
        total_likes = 0
        total_trophies = 0

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
        post = cursor.fetchall()

        for p in post:
            post_id = p['id']

            # Get the number of likes receive by user
            cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
            like_count_post = cursor.fetchone()
            total_likes += like_count_post['like_count_post']

            # Get the number of trophies reveive by user
            cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
            trophy_count_post = cursor.fetchone()
            total_trophies += trophy_count_post['trophy_count_post']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user ORDER BY user.user_id DESC')
        users = cursor.fetchall()

        cursor.execute('SELECT orders.*, user.name FROM orders JOIN user ON orders.user_id = user.user_id ORDER BY orders.id DESC')
        orders = cursor.fetchall()

        cursor.execute('SELECT withdraw.*, user.name FROM withdraw JOIN user ON withdraw.user_id = user.user_id ORDER BY withdraw.id DESC')
        withdraw = cursor.fetchall()

        cursor.execute('SELECT * FROM notice ORDER BY notice.id DESC')
        notice = cursor.fetchall()

        cursor.execute('SELECT * FROM prompt ORDER BY prompt.id DESC')
        prompt = cursor.fetchall()

        cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        cursor.execute('SELECT * FROM report ORDER BY report.id DESC')
        report = cursor.fetchall()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
        notification_count = cursor.fetchone()['notification_count']

        # Retrieve the notifications for the user
        cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
        notifications = cursor.fetchall()



        return render_template("admin.html", users=users, orders=orders, withdraw=withdraw, notice=notice, prompt=prompt, notifications=notifications, user=user, 
            notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies, report=report)
    else:
        return redirect(url_for('feed'))


#----------------prompt add section---------------------------
@app.route("/addprompt", methods=['POST'])
def add_prompt():
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    name = request.form.get('name')

    if request.method == "POST":
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO prompt (name, created_at) VALUES (%s, NOW())', (name,))
        mysql.connection.commit()


        return redirect(url_for('admin'))

#---------------prompt edit page -------------------------
@app.route('/promptedit/<prompt_id>', methods=['GET', 'POST'])
def edit_prompt(prompt_id):
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    name = request.form.get('name')

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE prompt SET name = %s WHERE id = %s', (name, prompt_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))


#----------------prompt delete section---------------------------
@app.route("/delete_prompt/<int:prompt_id>", methods=("POST",))
def delete_prompt(prompt_id):
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    # Post found and belongs to the logged-in user, delete it
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM prompt WHERE id = %s', (prompt_id,))
    mysql.connection.commit()

    return redirect(url_for('admin'))


#----------------notice add section---------------------------
@app.route("/addnotice", methods=['POST'])
def add_notice():
    name = request.form.get('name')

    if request.method == "POST":
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO notice (name, created_at) VALUES (%s, NOW())', (name,))
        mysql.connection.commit()


        return redirect(url_for('admin'))


#---------------notice edit page -------------------------
@app.route('/noticeedit/<notice_id>', methods=['GET', 'POST'])
def edit_notice(notice_id):
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    name = request.form.get('name')

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE notice SET name = %s WHERE id = %s', (name, notice_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))

#----------------notice delete section---------------------------
@app.route("/delete_notice/<int:notice_id>", methods=("POST",))
def delete_notice(notice_id):
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    # Post found and belongs to the logged-in user, delete it
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM notice WHERE id = %s', (notice_id,))
    mysql.connection.commit()

    return redirect(url_for('admin'))

#-----------Home Page-----------------
@app.route("/", methods=("GET", "POST"))
def home():

    if session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('feed'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM feed ORDER BY feed.id DESC')
    post = cursor.fetchall()

    post_array = []

    for p in post:
        post_id = p['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        # print("Comment Count:", comment_count['comment_count'])

        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()

        # Get the username of the user who created the post
        user_id = p['user_id']
        cursor.execute('SELECT name, profile FROM user WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        
        postObj = {
            'id': p['id'],
            'title': p['title'],
            'chunk': p['chunk'].strip().split('\n\n'),
            'category': p['category'],
            'file': p['file'],
            'tool': p['tool'],
            'name': user['name'],
            'profile': user['profile'],
            'comment_count': comment_count['comment_count'],
            'like_count': like_count['like_count'],
            'trophy_count': trophy_count['trophy_count'],

        }


        post_array.append(postObj)

    cursor.execute('SELECT * FROM prompt ORDER BY prompt.id')
    prompts = cursor.fetchall()
 

    return render_template("home.html", post=post_array, prompts=prompts)


#-------------NewsFeed for everyone Section----------------
@app.route("/newsfeed", methods=("GET", "POST"))
def newsfeed():

    if session.get('loggedin'):
        return redirect(url_for('feed'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM feed ORDER BY feed.id DESC')
    post = cursor.fetchall()

    post_array = []

    for p in post:
        post_id = p['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        # print("Comment Count:", comment_count['comment_count'])

        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()

        # Get the username of the user who created the post
        user_id = p['user_id']
        cursor.execute('SELECT name, profile FROM user WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        
        postObj = {
            'id': p['id'],
            'title': p['title'],
            'chunk': p['chunk'].strip().split('\n\n'),
            'category': p['category'],
            'file': p['file'],
            'tool': p['tool'],
            'name': user['name'],
            'profile': user['profile'],
            'comment_count': comment_count['comment_count'],
            'like_count': like_count['like_count'],
            'trophy_count': trophy_count['trophy_count'],

        }


        post_array.append(postObj)



    return render_template('newsfeed.html', post=post_array)


#-------------NewsFeed Section----------------
@app.route("/feed", methods=("GET", "POST"))
def feed():
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    user_id = session['user_id']
    post_array = []
    comment = []

    total_likes = 0
    total_trophies = 0

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()


    processed_posts = []

    for p in post:
        post_id = p['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        # print("Comment Count:", comment_count['comment_count'])

        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()

        # Get the number of likes receive by user
        cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
        like_count_post = cursor.fetchone()
        total_likes += like_count_post['like_count_post']

        # Get the number of trophies reveive by user
        cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count_post = cursor.fetchone()
        total_trophies += trophy_count_post['trophy_count_post']
        
        postObj = {
            'id': p['id'],
            'title': p['title'],
            'chunk': p['chunk'].strip().split('\n\n'),
            'user_id': p['user_id'],
            'category': p['category'],
            'file': p['file'],
            'name': p['name'],
            'profile': p['profile'],
            'tool': p['tool'],
            'comment_count': comment_count['comment_count'],
            'like_count': like_count['like_count'],
            'trophy_count': trophy_count['trophy_count'],


        }


        post_array.append(postObj)

    # Sort the posts based on like_count and trophy_count in descending order
    sorted_posts = sorted(post_array, key=lambda x: (-x['like_count'], -x['trophy_count']))

    cursor.execute('SELECT * FROM history WHERE user_id = %s ORDER BY id DESC', (user_id,))
    history = cursor.fetchall() 

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
    notification_count = cursor.fetchone()['notification_count']


    cursor.execute('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id ORDER BY comment.id DESC LIMIT 4')
    comment = cursor.fetchall()


    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
    # cursor.execute('SELECT * FROM notification WHERE user_id = %s ORDER BY id DESC', (user_id,))
    notifications = cursor.fetchall()

    # Get all ratings for the profile
    cursor.execute('SELECT rating_value FROM profile_rating WHERE profile_id = %s', (user_id,))
    ratings = cursor.fetchall()
    has_rated = bool(ratings)

    # Calculate the average rating
    if ratings:
        total_ratings = len(ratings)
        sum_ratings = sum(int(rating['rating_value']) for rating in ratings)
        average_rating = sum_ratings / total_ratings
    else:
        average_rating = None


    cursor.execute('SELECT u.user_id, u.name, COUNT(l.post_id) AS total_likes FROM user u LEFT JOIN feed f ON u.user_id = f.user_id LEFT JOIN likes l ON f.id = l.post_id GROUP BY u.user_id, u.name;')
    user_like = cursor.fetchall()

    cursor.execute('SELECT u.user_id, u.name, COUNT(l.post_id) AS total_trophies FROM user u LEFT JOIN feed f ON u.user_id = f.user_id LEFT JOIN trophy l ON f.id = l.post_id GROUP BY u.user_id, u.name;')
    user_trophy = cursor.fetchall()

    combined_data = []

    # Create dictionaries for user_like and user_trophy data for easy access
    user_like_dict = {data['user_id']: data for data in user_like}
    user_trophy_dict = {data['user_id']: data for data in user_trophy}

    # Combine and adjust data
    for user_id, like_data in user_like_dict.items():
        if user_id in user_trophy_dict:
            name = like_data['name']
            total_rank = like_data['total_likes'] + user_trophy_dict[user_id]['total_trophies'] * 25
            combined_data.append({'user_id': user_id, 'name': name, 'total_rank': total_rank})

    sorted_combined_data = sorted(combined_data, key=lambda x: x['total_rank'], reverse=True)

    #Get the number of followed user
    cursor.execute('SELECT COUNT(*) AS follower_count FROM follows WHERE follower_id = %s', (user_id,))
    follower_count = cursor.fetchone()['follower_count']

    #show notice from admin 
    cursor.execute('SELECT * FROM notice ORDER BY notice.id DESC LIMIT 5')
    notice = cursor.fetchall()

    cursor.execute('SELECT * FROM prompt ORDER BY prompt.id')
    prompts = cursor.fetchall()

    cursor.execute('SELECT * FROM user ORDER BY user.user_id')
    users = cursor.fetchall()

    trophy_user_post = get_liked_posts_for_user(user_id)


    return render_template("feed.html", post=sorted_posts, comment=comment, history=history, notifications=notifications, user=user, users=users, notification_count=notification_count,
        average_rating=average_rating, total_likes=total_likes, total_trophies=total_trophies,follower_count=follower_count, notice=notice, prompts=prompts, user_like=user_like,
        user_trophy=user_trophy, rank=sorted_combined_data, trophy_user_post=trophy_user_post)



def get_liked_posts_for_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT post_id FROM trophy WHERE user_id = %s', (user_id,))
    trophy_user_post = [row['post_id'] for row in cursor.fetchall()]
    cursor.close()
    return trophy_user_post






#---------------feed search top nav -------------------------
@app.route('/api/users', methods=['GET'])
def get_users():
    search_query = request.args.get('q', '').strip().upper()

    if not search_query:
        return jsonify([])

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT user_id, name FROM user WHERE name LIKE %s", ('%' + search_query + '%',))
    data = cursor.fetchall()
    cursor.close()

    user_info = [{'user_id': user[0], 'name': user[1]} for user in data]
    return jsonify(user_info)



#---------------feed notification top nav -------------------------
@app.route('/notification/<notification_id>/read', methods=['GET', 'POST'])
def mark_notification_as_read(notification_id):
    user_id = session['user_id']

    if not user_id:
        return "User not logged in"  # You might want to handle this case more gracefully

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE notification SET is_read = %s WHERE id = %s AND user_id = %s', (1, notification_id, user_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('feed'))




#---------------user profile page -------------------------
@app.route("/profile/<int:user_id>", methods=("GET", "POST"))
def profile(user_id):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get all posts of the particular user
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id WHERE user.user_id = %s ORDER BY feed.id DESC', (user_id,))
    user_posts = cursor.fetchall()


    total_likes = 0
    total_trophies = 0

    price_per_like = 0.01
    price_per_trophy = 0.25

    for post in user_posts:
        post_id = post['id']

        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
        like_count_post = cursor.fetchone()
        total_likes += like_count_post['like_count_post']

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count_post = cursor.fetchone()
        total_trophies += trophy_count_post['trophy_count_post']


    # Calculate the total cost of likes and trophies in cents
    total_likes_cost = total_likes * price_per_like
    total_trophies_cost = total_trophies * price_per_trophy

    # Calculate the total price in cents
    total_price_cents = total_likes_cost + total_trophies_cost


    if not user:
        return "User not found"


    # Check if the logged-in user is already following the profile user
    follower_id = session['user_id']

    if user_id == follower_id:
        own_profile = True

    else:
        own_profile = False

        # Fetch the current view count
        cursor.execute('SELECT count FROM view_count WHERE user_id = %s AND profile_id = %s', (follower_id, user_id))
        count = cursor.fetchone()

        if count:
            # If the entry exists, increment the view count
            cursor.execute('UPDATE view_count SET count = count + 1 WHERE user_id = %s AND profile_id = %s', (follower_id, user_id))
            mysql.connection.commit()
        else:
            # If the entry doesn't exist, insert a new record with view count as 1
            cursor.execute('INSERT INTO view_count (user_id, profile_id, count) VALUES (%s, %s, 1)', (follower_id, user_id))
            mysql.connection.commit()

    # Fetch the view count from the database
    if not own_profile:
        cursor.execute('SELECT count FROM view_count WHERE user_id = %s AND profile_id = %s', (follower_id, user_id))
        count = cursor.fetchone()['count']
    else:
        count = 0  # Set the view count to 0 for the user's own profile


    # Get all ratings for the profile
    cursor.execute('SELECT rating_value FROM profile_rating WHERE profile_id = %s', (user_id,))
    ratings = cursor.fetchall()
    has_rated = bool(ratings)

    # Calculate the average rating
    if ratings:
        total_ratings = len(ratings)
        sum_ratings = sum(int(rating['rating_value']) for rating in ratings)
        average_rating = sum_ratings / total_ratings
    else:
        average_rating = None


    cursor.execute("SELECT * FROM follows WHERE follower_id = %s AND following_id = %s", (follower_id, user_id))
    is_following = cursor.fetchone()

    cursor.execute('SELECT COUNT(*) AS history_count FROM history WHERE user_id = %s', (user_id,))
    history_count = cursor.fetchone()['history_count']

    cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE user_id = %s', (user_id,))
    like_count = cursor.fetchone()['like_count']

    cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE user_id = %s', (user_id,))
    trophy_count = cursor.fetchone()['trophy_count']

    cursor.execute('SELECT id FROM feed WHERE user_id = %s', (user_id,))
    profile_user_posts = cursor.fetchall()
    profile_user_post_ids = [post['id'] for post in profile_user_posts]

    # Fetch the trophies given by the logged-in user to the profile user's posts
    if not profile_user_post_ids:
        trophies_given = []  # If there are no post_ids, there won't be any trophies
    else:
        placeholders = ', '.join(['%s'] * len(profile_user_post_ids))
        query = "SELECT * FROM trophy WHERE user_id = %s AND post_id IN ({})".format(placeholders)
        cursor.execute(query, (follower_id,) + tuple(profile_user_post_ids))
        trophies_given = cursor.fetchall()

    has_given_trophies = bool(trophies_given)

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (follower_id,))
    notification_count = cursor.fetchone()['notification_count']

    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (follower_id,))
    notifications = cursor.fetchall()

    cursor.execute('SELECT * FROM user ORDER BY user.user_id')
    users = cursor.fetchall()

    


    return render_template("profile.html", user=user, users=users, total_likes=total_likes, total_likes_cost=total_likes_cost, total_trophies_cost=total_trophies_cost, 
        total_price_cents=total_price_cents, total_trophies=total_trophies, history_count=history_count, like_count=like_count, trophy_count=trophy_count, 
        is_following=is_following, own_profile=own_profile, count=count, average_rating=average_rating, has_given_trophies=has_given_trophies,
        notifications=notifications, notification_count=notification_count)


#------------------user edit profile page----------------------
@app.route("/edit/<int:user_id>", methods=["GET", "POST"])
def edit(user_id):

    total_likes = 0
    total_trophies = 0

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()

    for p in post:
        post_id = p['id']

        # Get the number of likes receive by user
        cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
        like_count_post = cursor.fetchone()
        total_likes += like_count_post['like_count_post']

        # Get the number of trophies reveive by user
        cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count_post = cursor.fetchone()
        total_trophies += trophy_count_post['trophy_count_post']

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
    notification_count = cursor.fetchone()['notification_count']

    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
    notifications = cursor.fetchall()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()

    return render_template("edit.html", user=user, notifications=notifications,
        notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies)


#----------------user edit profile form----------------------
@app.route("/edit_profile/<int:user_id>", methods=["POST"])
def edit_profile(user_id):
    if request.method == "POST":
        file = request.files['profile']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

    
        if file:
            # Save the file to AWS S3 bucket
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            filename = secure_filename(file.filename)
            s3.upload_fileobj(file, BUCKET_NAME, filename)

            # Get the S3 URL for the uploaded file
            s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
            file_path = s3_url
       
        else:
            file_path = ""


        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE user SET name = %s, email = %s, password = %s, profile = %s WHERE user_id = %s',
                       (name, email, password, file_path, user_id))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('profile', user_id=user_id))

    return render_template('profile.html', user_id=user_id)



# ---------------------------Profile Rating Section-----------------------------------
@app.route("/submit_rating/<int:profile_id>", methods=["POST"])
def submit_rating(profile_id):
    # Get the logged-in user's ID from the session
    user_id = session["user_id"]

    if request.method == "POST":
        # Get the rating_value from the submitted form data
        rating_value = request.form.get("rating_value")


        # Check if the logged-in user has already rated the profile
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT rating_value FROM profile_rating WHERE user_id = %s AND profile_id = %s",
            (user_id, profile_id)
        )
        rating = cursor.fetchone()

        if rating:
            # User has already rated, update the existing rating
            cursor.execute("UPDATE profile_rating SET rating_value = %s WHERE user_id = %s AND profile_id = %s", (rating_value, user_id, profile_id))
        else:
            # Insert the rating into the database
            cursor.execute(
                "INSERT INTO profile_rating (user_id, profile_id, rating_value) VALUES (%s, %s, %s)",
                (user_id, profile_id, rating_value)
            )

        mysql.connection.commit()

        # Calculate the updated average rating
        cursor.execute("SELECT AVG(rating_value) AS average_rating FROM profile_rating WHERE profile_id = %s", (profile_id,))
        average_rating = cursor.fetchone()[0]


        flash("Thank you for rating!")

    return redirect(url_for("profile", user_id=profile_id))
    



# ---------------------------Products Section-----------------------------------
@app.route('/tokenbuy', methods=['GET'])
def tokenbuy():
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    user_id = session["user_id"]

    total_likes = 0
    total_trophies = 0

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()

    for p in post:
        post_id = p['id']

        # Get the number of likes receive by user
        cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
        like_count_post = cursor.fetchone()
        total_likes += like_count_post['like_count_post']

        # Get the number of trophies reveive by user
        cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count_post = cursor.fetchone()
        total_trophies += trophy_count_post['trophy_count_post']

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
    notification_count = cursor.fetchone()['notification_count']

    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
    notifications = cursor.fetchall()


    # Retrieve products from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM product")
    product = cursor.fetchall()


    cursor.execute('SELECT * FROM user ORDER BY user.user_id')
    users = cursor.fetchall()

    cursor.close()

    return render_template('tokenbuy.html', product=product, notifications=notifications, user=user, users=users, 
        notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies)


#----------------------token payment------------------------
@app.route('/token_payment', methods=['POST'])
def token_payment():
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        price = float(request.form['price'])
        qty = calculate_qty(price)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Retrieve the user's current token_balance
        cursor.execute('SELECT token_balance FROM user WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        current_balance = result['token_balance']

        # Calculate the updated token_balance after payment
        updated_balance = current_balance + int(qty)

        # Update the user's token_balance in the database
        cursor.execute('UPDATE user SET token_balance = %s WHERE user_id = %s', (updated_balance, user_id))
        mysql.connection.commit()

   
        cursor.execute('INSERT INTO orders (user_id, price, qty) VALUES (%s, %s, %s)', (user_id, price, qty,))
        mysql.connection.commit()

        data = {'status': 'Payment successfully'}
        return jsonify(data)


def calculate_qty(price):

    return price * 96



# ---------------------------Order Page-----------------------------------
@app.route('/order', methods=['GET'])
def order():
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    user_id = session['user_id']

    total_likes = 0
    total_trophies = 0

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()

    for p in post:
        post_id = p['id']

        # Get the number of likes receive by user
        cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
        like_count_post = cursor.fetchone()
        total_likes += like_count_post['like_count_post']

        # Get the number of trophies reveive by user
        cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count_post = cursor.fetchone()
        total_trophies += trophy_count_post['trophy_count_post']

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
    notification_count = cursor.fetchone()['notification_count']

    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
    notifications = cursor.fetchall()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT orders.*, user.name FROM orders JOIN user ON orders.user_id = user.user_id WHERE orders.user_id = %s ORDER BY orders.id DESC', (user_id,))
    # cursor.execute("SELECT * FROM orders WHERE user_id = %s", (user_id,))
    orders = cursor.fetchall()
    cursor.close()
 
    return render_template('order.html', orders=orders, notifications=notifications, user=user, 
        notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies)


# ------------------Withdraw money by user by user----------------------
@app.route('/withdraw', methods=['POST'])
def withdraw():
    if request.method == "POST":
        user_id = request.form.get('user_id')
        email = request.form.get('email')
        name = request.form.get('name')
        bank_name = request.form.get('bank_name')
        routing_name = request.form.get('routing_name')
        account_num = request.form.get('account_num')
        amt = request.form.get('amt')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO withdraw (user_id, name, email, bank_name, routing_name, account_num, amt, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())', (user_id, name, email, bank_name, routing_name, account_num, amt))
        mysql.connection.commit()

    return redirect(url_for('thank_you'))


# ------------------Rport problem by user----------------------
@app.route('/report', methods=['POST'])
def report():
    if request.method == "POST":
        email = request.form.get('email')
        name = request.form.get('name')
        title = request.form.get('title')
        message = request.form.get('message')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO report (name, email, title, message, created_at) VALUES (%s, %s, %s, %s, NOW())', (name, email, title, message))
        mysql.connection.commit()

    return redirect(url_for('thank_you'))



#---------------------show follower user in circle tab-------------------
@app.route("/followed_users", methods=["GET"])
def get_followed_users():
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    follower_id = session['user_id']


    total_likes = 0
    total_trophies = 0

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()

    for p in post:
        post_id = p['id']

        # Get the number of likes receive by user
        cursor.execute('SELECT COUNT(*) AS like_count_post FROM likes WHERE post_id = %s', (post_id,))
        like_count_post = cursor.fetchone()
        total_likes += like_count_post['like_count_post']

        # Get the number of trophies reveive by user
        cursor.execute('SELECT COUNT(*) AS trophy_count_post FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count_post = cursor.fetchone()
        total_trophies += trophy_count_post['trophy_count_post']
        


    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT following_id FROM follows WHERE follower_id = %s", (follower_id,))
    followed_users = cursor.fetchall()

    # cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # cursor.execute("SELECT following_id FROM follows WHERE follower_id = %s", (follower_id,))
    # user_id = cursor.fetchone()

    # cursor.execute("SELECT * FROM follows WHERE follower_id = %s AND following_id = %s", (follower_id, user_id))
    # is_following = cursor.fetchone()

    # Fetch the names of the followed users from the user table
    followed_users_info = []
    for user in followed_users:
        cursor.execute('SELECT * FROM user WHERE user_id = %s', (user['following_id'],))
        user_info = cursor.fetchone()
        followed_users_info.append(user_info)


    cursor.execute('SELECT * FROM user WHERE user_id = %s', (follower_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (follower_id,))
    notification_count = cursor.fetchone()['notification_count']

    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (follower_id,))
    notifications = cursor.fetchall()

    cursor.execute('SELECT * FROM user ORDER BY user.user_id')
    users = cursor.fetchall()

    return render_template("followedUser.html", followed_users=followed_users_info, notifications=notifications, user=user, users=users, notification_count=notification_count,
        total_likes=total_likes, total_trophies=total_trophies)



#--------------------------follow user in profile---------------------
@app.route("/follow/<int:user_id>", methods=["POST"])
def follow(user_id):
    if 'loggedin' not in session:
        return redirect(url_for('home'))


    follower_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("INSERT INTO follows (follower_id, following_id, created_at) VALUES (%s, %s, NOW())", (follower_id, user_id))
    mysql.connection.commit()

    # Check if the action resulted in a mutual follow relationship
    cursor.execute("SELECT * FROM follows WHERE follower_id = %s AND following_id = %s", (user_id, follower_id))
    mutual_follow = cursor.fetchone()

    # Fetch the post owner's name
    cursor.execute('SELECT name FROM user WHERE user_id = %s', (follower_id,))
    username = cursor.fetchone()['name']

    if not mutual_follow:
        notification = "{} is now following you.".format(username)
        # Save the notification in the database
        cursor.execute("INSERT INTO notification (user_id, message, created_at) VALUES (%s, %s, NOW())", (user_id, notification))
        mysql.connection.commit()

    return redirect(url_for('profile', user_id=user_id))


#--------------------------unfollow user in profile---------------------
@app.route("/unfollow/<int:user_id>", methods=["POST"])
def unfollow(user_id):
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    follower_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM follows WHERE follower_id = %s AND following_id = %s", (follower_id, user_id))
    mysql.connection.commit()

    # Check if the action resulted in the removal of a mutual follow relationship
    cursor.execute("SELECT * FROM follows WHERE follower_id = %s AND following_id = %s", (user_id, follower_id))
    mutual_follow = cursor.fetchone()

    # Fetch the post owner's name
    cursor.execute('SELECT name FROM user WHERE user_id = %s', (follower_id,))
    username = cursor.fetchone()['name']

    if not mutual_follow:
        notification = "{} has unfollowed you.".format(username)
        # Save the notification in the database
        cursor.execute("INSERT INTO notification (user_id, message, created_at) VALUES (%s, %s, NOW())", (user_id, notification))
        mysql.connection.commit()

    return redirect(url_for('profile', user_id=user_id))



# ------------------Create post by user----------------------
@app.route('/create_post', methods=['POST'])
def create_post():
    if request.method == "POST":
        chunk = request.form.get('chunk')
        user_id = request.form.get('user_id')
        category = request.form.get('category')
        title = request.form.get('paste_prompt')
        file = request.files['file']
        video = request.files['video_file']
        tool = request.form.get('tool')

        if file:
            # Save the file to AWS S3 bucket
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            filename = secure_filename(file.filename)
            s3.upload_fileobj(file, BUCKET_NAME, filename)

            # Get the S3 URL for the uploaded file
            s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
            file_path = s3_url

        elif video:
            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
            video_filename = secure_filename(video.filename)
            s3.upload_fileobj(video, BUCKET_NAME, video_filename)

            # Get the S3 URL for the uploaded video file
            video_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{video_filename}"
            file_path = video_s3_url
       
        else:
            file_path = ""

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO feed (chunk, user_id, file, category, title, tool, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())', (chunk, user_id, file_path, category, title, tool))
        mysql.connection.commit()

        # Get all the followers of the user posting the content
        cursor.execute("SELECT follower_id FROM follows WHERE following_id = %s", (user_id,))
        followers = cursor.fetchall()

        # Fetch the post owner's username
        cursor.execute('SELECT name FROM user WHERE user_id = %s', (user_id,))
        username = cursor.fetchone()['name']

        for follower in followers:
            follower_id = follower['follower_id']
            message = f"{username} posted something new."
            cursor.execute("INSERT INTO notification (user_id, message, created_at) VALUES (%s, %s, NOW())", (follower_id, message))
            mysql.connection.commit()

        flash('You have posted successfully', 'success')


    return redirect(url_for('feed'))


#----------------post delete section---------------------------
@app.route("/delete_post/<int:post_id>", methods=("POST",))
def delete_post(post_id):
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM feed WHERE id = %s AND user_id = %s', (post_id, user_id))
    post = cursor.fetchone()

    if post:
        # Post found and belongs to the logged-in user, delete it
        cursor.execute('DELETE FROM feed WHERE id = %s', (post_id,))
        mysql.connection.commit()

    return redirect(url_for('feed'))


#----------------------Reward like section---------------------
@app.route("/like_post/<int:post_id>", methods=["GET"])
def like_post(post_id):
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))
    like = cursor.fetchone()

    cursor.execute('SELECT * FROM feed WHERE id = %s', (post_id,))
    post = cursor.fetchone()

    if not post:
        flash("Post does not exist.")

    else:
        cursor.execute('SELECT token_balance FROM user WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if user['token_balance'] <= 0:
            flash("Not enough token balance.")
            return redirect(url_for('feed'))

        elif not like:
            cursor.execute('INSERT INTO likes (user_id, post_id) VALUES (%s, %s)', (user_id, post_id))
            cursor.execute('UPDATE user SET token_balance = token_balance - 1 WHERE user_id = %s', (user_id,))
            mysql.connection.commit()

            # Update the like count in the post
            cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
            like_count = cursor.fetchone()['like_count']

            # Fetch the post owner's user ID
            cursor.execute('SELECT user_id FROM feed WHERE id = %s', (post_id,))
            user_id = cursor.fetchone()['user_id']

            # Fetch the post owner's name
            cursor.execute('SELECT name FROM user WHERE user_id = %s', (user_id,))
            username = cursor.fetchone()['name']

            notification = "{} rewarded your post.".format(username)
            cursor.execute('INSERT INTO notification (user_id, message, created_at) VALUES (%s, %s, NOW())', (user_id, notification))
            mysql.connection.commit()

            return jsonify(like_count=like_count)
        else:
            # If the user has already liked the post, return the current like count
            cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
            like_count = cursor.fetchone()['like_count']

            return jsonify(like_count=like_count)
        




#-----------------trophy share section----------------------
@app.route("/trophy_post/<int:post_id>", methods=["GET"])
def trophy_post(post_id):
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, user_id))
    trophy = cursor.fetchone()

    cursor.execute('SELECT * FROM feed WHERE id = %s', (post_id,))
    post = cursor.fetchone()

    if not post:
        flash("Post does not exist..")

    else:
        cursor.execute('SELECT token_balance FROM user WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if user['token_balance'] <= 25:
            flash("Not enough token balance.", 'error')
            return redirect(url_for('feed'))


        elif not trophy:
            cursor.execute('INSERT INTO trophy (user_id, post_id) VALUES (%s, %s)', (user_id, post_id))
            cursor.execute('UPDATE user SET token_balance = token_balance - 25 WHERE user_id = %s', (user_id,))
            mysql.connection.commit() 

            # Update the trophy count in the post
            cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
            trophy_count = cursor.fetchone()['trophy_count']

            # Fetch the post owner's user ID
            cursor.execute('SELECT user_id FROM feed WHERE id = %s', (post_id,))
            user_id = cursor.fetchone()['user_id']

            # Fetch the post owner's name
            cursor.execute('SELECT name FROM user WHERE user_id = %s', (user_id,))
            username = cursor.fetchone()['name']

            notification = "{} awarded a trophy to your post.".format(username)
            cursor.execute('INSERT INTO notification (user_id, message, created_at) VALUES (%s, %s, NOW())', (user_id, notification))
            mysql.connection.commit()

            # Return the updated trophy count as JSON response
            return jsonify(trophy_count=trophy_count)
        else:
            # If the user has already liked the post, return the current like count
            cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
            trophy_count = cursor.fetchone()['trophy_count']

            return jsonify(trophy_count=trophy_count)  




# -------------------------Create comment-----------------------------
@app.route("/create_comment/<int:post_id>", methods=("POST",))
def create_comment(post_id):
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    text = request.form.get('text')
    user_id = session['user_id']
    user_name = session['name']


    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM feed WHERE id = %s',(post_id,))
    post = cursor.fetchone()

    if post:
        # Post found and belongs to the logged-in user, delete it
        cursor.execute('INSERT INTO comment (text, user_id, post_id) VALUES (%s, %s, %s)', (text, user_id, post_id))
        mysql.connection.commit()

    new_comment = {
        'name': user_name,  # Replace with the user's name
        'text': text,
        # Add any other comment-related data here as needed
    }

    return jsonify(new_comment)

    # return redirect(url_for('feed'))




#------------- Store the data produce by openai to db----------------------
@app.route("/store_data", methods=['POST'])
def store_data():
    chunk_data = request.form.get('chunks')
    chunks = json.loads(chunk_data)
    title_data = request.form.get('title')
    cat_data = request.form.get('cat')
    user_id = request.form.get('user_id')
    category = request.form.get('radioInput')
    post = request.form["post"]
    

    if title_data:
        title = json.loads(title_data)
    elif category:
        title = category + " " + post
    else:
        title = ""


    if cat_data:
        category = json.loads(cat_data)
    else:
        category = request.form.get('radioInput')


    combined_chunks = '\n\n'.join(chunks)



    if request.method == "POST" and 'list-add' in request.form:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO feed (title, chunk, user_id, category, created_at) VALUES (%s, %s, %s, %s, NOW())', (title, combined_chunks, user_id, category))
        mysql.connection.commit()

        # Retrieve the followers of the current user
        cursor.execute('SELECT follower_id FROM follows WHERE following_id = %s', (user_id,))
        followers = cursor.fetchall()

        # Fetch the post owner's username
        cursor.execute('SELECT name FROM user WHERE user_id = %s', (user_id,))
        username = cursor.fetchone()['name']

        for follower in followers:
            follower_id = follower['follower_id']
            message = f"{username} posted something new."
            cursor.execute("INSERT INTO notification (user_id, message, created_at) VALUES (%s, %s, NOW())", (follower_id, message))
            mysql.connection.commit()

        return redirect(url_for('feed'))


@app.route('/stream')
def stream():

    reqUrl = 'https://api.openai.com/v1/completions'
    reqHeaders = {
        'Accept': 'text/event-stream',
        'Authorization': 'Bearer ' + openai.api_key
    }
    reqBody = {
        "model": model_engine,
        "prompt": "write about canada",
        "max_tokens": 100,
        "temperature": 0,
        "stream": True,
    }

    def generate():
        request = requests.post(reqUrl, stream=True, headers=reqHeaders, json=reqBody)
        client = sseclient.SSEClient(request)
        for event in client.events():
            if event.data != '[DONE]':
                yield f"data: {event.data}\n\n"

    return app.response_class(generate(), mimetype='text/event-stream')


#------------render data from openai and save to history----------
@app.route('/feed_generate', methods=['POST'])
def feed_generate():


    if request.method == "POST":
        post = request.form["post"]
        user_id = request.form["user_id"]
        selection = request.form["selection"]
        animal = selection + " " + post

        reqUrl = 'https://api.openai.com/v1/completions'
        reqHeaders = {
            'Authorization': 'Bearer ' + openai.api_key
        }
        reqBody = {
            "model": "text-davinci-003",
            "prompt": animal,
            "max_tokens": 2049,
            "temperature": 0.05,
            "stream": True,
        }

        def generate():
            request_data = requests.post(reqUrl, stream=True, headers=reqHeaders, json=reqBody)
            client = sseclient.SSEClient(request_data)
            
            for event in client.events():
                if event.data != '[DONE]':
                    print(f"Received event data: {event.data}")
                    yield f"data: {event.data}\n\n"

        return Response(generate(), content_type='text/event-stream')



#------------render data from openai and save to history----------
@app.route('/feed_generate', methods=['POST'])
def feed_generate():  
    post = request.form["post"]
    user_id = request.form["user_id"]
    selection = request.form["selection"]
    animal = selection + " " + post

    chunks = request.form.getlist("chunk")



    if request.method == "POST":


        animal = animal

        chunks = []
        
        response = openai.Completion.create(
            engine=model_engine,
            prompt=generate_feed(animal),
            max_tokens=2049,
            n=1,
            stop=None,
            temperature=0.05,
        )

        text = response.choices[0].text
        chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)

        combined_chunks = '\n\n'.join(chunks)

        #add to database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO history (title, content, user_id, category) VALUES (%s, %s, %s, %s)', (animal, combined_chunks, user_id, selection))
        mysql.connection.commit()


        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM history')
        history = cursor.fetchall()

        return jsonify({
            'chunks': chunks,
            'history': history
        })

   
    chunks = request.args.get("chunks")
    if chunks is not None:
        chunks = chunks.split(",")

    return jsonify({
            'chunks': chunks,

        })




def generate_feed(animal):
    prompt = f"Write about {animal}"
    return prompt




#-------------------show generate page----------------
@app.route("/content", methods=("GET", "POST"))
def content():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM history ORDER BY id DESC')
    history = cursor.fetchall() 

    cursor.execute('SELECT * FROM prompt ORDER BY prompt.id')
    prompts = cursor.fetchall()

    return render_template("content.html", history=history, prompts=prompts)

#------------render data from openai and save to history----------
@app.route('/content_process', methods=['POST'])
def content_process():  
    post = request.form["post"]
    user_id = request.form["user_id"]
    selection = request.form["selection"]
    animal = selection + " " + post

    chunks = request.form.getlist("chunk")


    # Perform further processing here instead of return value
    form_disabled = False
    form_submitted_key = 'my_form_submitted_key'
    form_disabled_key = 'my_form_disabled_key'

    # Check if form has been submitted before
    num_submissions = session.get(form_submitted_key, 0)

    if request.method == "POST":
        # Form has been submitted
        session[form_submitted_key] = num_submissions + 1

        if num_submissions >= 1:
            # Disable form after 10 submissions
            session[form_disabled_key] = True

        form_disabled = session.get(form_disabled_key, False)

        animal = animal

        chunks = []
        
        response = openai.Completion.create(
            engine=model_engine,
            prompt=generate_content(animal),
            max_tokens=2049,
            n=1,
            stop=None,
            temperature=0.05,
        )

        # Split the response text into chunks
        text = response.choices[0].text
        chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)

        combined_chunks = '\n\n'.join(chunks)

        #add to database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO history (title, content, user_id, category) VALUES (%s, %s, %s, %s)', (animal, combined_chunks, user_id, selection))
        mysql.connection.commit()
        cursor.close()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM history')
        history = cursor.fetchall()

        return jsonify({
            'chunks': chunks,
            'form_disabled': form_disabled,
            'history': history
        })


        # return redirect(url_for('feed', chunks=chunks, form_disabled=form_disabled, history=history))


    # Check if form should be disabled
    form_disabled = session.get(form_disabled_key, False)

    chunks = request.args.get("chunks")
    if chunks is not None:
        chunks = chunks.split(",")

    return jsonify({
            'chunks': chunks,
            'form_disabled': form_disabled,

        })

    # return redirect(url_for('feed', chunks=chunks, form_disabled=form_disabled))


def generate_content(animal):
    prompt = f"Write about {animal}"
    return prompt



# -------------------------Personalize education--------------------------------
@app.route("/studentDashboard", methods=("GET", "POST"))
def studentDashboard():

    return render_template("studentDashboard.html")

# Personalize education
@app.route('/process', methods=['POST'])
def process():  
    grade = request.form["grade"]
    subject = request.form["subject"]
    animal = grade + " " + subject

    # Perform further processing here instead of return value

    form_disabled = False
    form_submitted_key = 'my_form_submitted_key'
    form_disabled_key = 'my_form_disabled_key'

    # Check if form has been submitted before
    num_submissions = session.get(form_submitted_key, 0)


    if request.method == "POST" and 'form-add' in request.form:
        
        # Form has been submitted
        session[form_submitted_key] = num_submissions + 1

        if num_submissions >= 100:
            # Disable form after 10 submissions
            session[form_disabled_key] = True

        form_disabled = session.get(form_disabled_key, False)

        animal = animal
        
        response = openai.Completion.create(
            engine=model_engine,
            prompt=generate_peducation(animal),
            max_tokens=250,
            n=1,
            stop=None,
            temperature=0.05,
        )
        
        # Split the response text into chunks
        text = response.choices[0].text
        chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)

        return redirect(url_for('content', chunks=chunks, form_disabled=form_disabled))

    # Check if form should be disabled
    form_disabled = session.get(form_disabled_key, False)

    chunks = request.args.get("chunks")
    if chunks is not None:
        chunks = chunks.split(",")

    return redirect(url_for('content', chunks=chunks, form_disabled=form_disabled))


def generate_peducation(animal):
    return """ {}
""".format(
        animal.capitalize()
    )





# ---------------------------Education query-----------------------------------
@app.route("/education", methods=("GET", "POST"))
def education():
    form_disabled = False
    form_submitted_key = 'my_form_submitted_key'
    form_disabled_key = 'my_form_disabled_key'

    # Check if form has been submitted before
    num_submissions = session.get(form_submitted_key, 0)


    if request.method == "POST" and 'form-add' in request.form:
        
        # Form has been submitted
        session[form_submitted_key] = num_submissions + 1

        if num_submissions >= 100:
            # Disable form after 10 submissions
            session[form_disabled_key] = True

        form_disabled = session.get(form_disabled_key, False)

        animal = request.form["animal"]
        
        response = openai.Completion.create(
            engine=model_engine,
            prompt=prompt_education(animal),
            max_tokens=250,
            n=1,
            stop=None,
            temperature=0.05,
        )
        
        # Split the response text into chunks
        text = response.choices[0].text
        # chunks = [text[i:i+MAX_CHARS_PER_CHUNK] for i in range(0, len(text), MAX_CHARS_PER_CHUNK)]
        chunks = split_text_into_list(text, MAX_CHARS_PER_CHUNK)

        return render_template("index.html", chunks=chunks, form_disabled=form_disabled)


    if request.method == "POST" and 'correct-grammer' in request.form:
        
        # Form has been submitted
        session[form_submitted_key] = num_submissions + 1

        if num_submissions >= 100:
            # Disable form after 10 submissions
            session[form_disabled_key] = True

        form_disabled = session.get(form_disabled_key, False)

        animal = request.form["animal"]
        
        response = openai.Completion.create(
            engine= model_engine,
            prompt=correct_grammer(animal),
            max_tokens=250,
            n=1,
            stop=None,
            temperature=0.05,
        )
        
        # Split the response text into chunks
        text = response.choices[0].text
        # chunks = [text[i:i+MAX_CHARS_PER_CHUNK] for i in range(0, len(text), MAX_CHARS_PER_CHUNK)]
        chunks = split_text_into_list(text, MAX_CHARS_PER_CHUNK)

        return render_template("index.html", chunks=chunks, form_disabled=form_disabled)
    # Check if form should be disabled
    form_disabled = session.get(form_disabled_key, False)

    chunks = request.args.get("chunks")
    if chunks is not None:
        chunks = chunks.split(",")

    return render_template("index.html", chunks=chunks, form_disabled=form_disabled)



def prompt_education(animal):
    prompt = f"Search information about {animal}"
    return prompt


def correct_grammer(animal):
    return """
       Correct it to standard english.
Sentence: I ply games.
Correct: I play games.
Sentence: {}
Correct:""".format(
        animal.capitalize()
    )







#split into paragraph
def split_text_into_chunks(text, max_chars_per_chunk):
    #we are splitting the text into paragraphs using the newline character.
    paragraphs = text.split("\n")

    #We initializes two empty lists chunks to store the final chunks and current_chunk to keep track of the current chunk being built.
    chunks = []
    current_chunk = ""

    #First we iterate over each paragraph
    for paragraph in paragraphs:
        #We check if the length of the current_cunk and paragraph is less than or equal to max character per chunk
        #If its true than the current paragraph is added to the current chunk.
        if len(current_chunk) + len(paragraph) <= max_chars_per_chunk:
            current_chunk += paragraph

        #here, the current chunk is added to the chunks list after stripping any leading or trailing whitespace.
        else:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
    
    #if there are remaining chunks left after the loop than than add that to the chunks as well
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

#split into list
def split_text_into_list(text, max_chars_per_chunk):
    # Split the text into paragraphs using the newline character.
    paragraphs = text.split("\n")

    # Initialize two empty lists: chunks to store the final chunks and current_chunk to keep track of the current chunk being built.
    chunks = []
    current_chunk = ""

    # Iterate over each paragraph.
    for paragraph in paragraphs:
        # Use regular expressions to identify list patterns ("1. ", "2. ", "3. ", etc.).
        list_pattern = re.compile(r"\d+\.\s")
        matches = list_pattern.finditer(paragraph)
        indices = [match.start() for match in matches]

        # If there are no list indices, add the entire paragraph as a chunk.
        if not indices:
            chunks.append(paragraph.strip())
            continue

        # Add the substring from the start of the paragraph to the first list index as a chunk.
        first_index = indices[0]
        if first_index > 0:
            chunks.append(paragraph[:first_index].strip())

        # Split the paragraph into chunks based on the list indices.
        for i in range(len(indices) - 1):
            start_index = indices[i]
            end_index = indices[i+1]
            chunk = paragraph[start_index:end_index].strip()
            chunks.append(chunk)

        # Add the remaining portion of the paragraph as the last chunk.
        last_index = indices[-1]
        last_chunk = paragraph[last_index:].strip()
        if last_chunk:
            chunks.append(last_chunk)

    return chunks



def calculate_delay(text):
    words_per_second = WORDS_PER_MINUTE / 60
    num_words = len(text.split())
    delay = num_words / words_per_second
    return delay

def sleep(value):
    delay = calculate_delay(value)
    time.sleep(delay)
    return Markup('')




#-----------------------Google Login-------------------------
@app.route('/google/login')
def google_login():
    return google.authorize(callback=url_for('google_callback', _external=True))


#---------------------Google callback function------------------------
@app.route('/google/callback')
@google.authorized_handler
def google_callback(resp):
    if resp is None or 'access_token' not in resp:
        return "Access denied: reason={0} error={1}".format(
            request.args['error_reason'],
            request.args['error_description']
        )

    access_token = resp['access_token']
    google_user_data = google.get('userinfo', token=(access_token, '')).data

    # Assuming you have a 'user' table in your MySQL database.
    # Create the user entry or update it if the email already exists.
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE email = %s', (google_user_data['email'],))
    user = cursor.fetchone()

    full_name = google_user_data.get('given_name', '') + ' ' + google_user_data.get('family_name', '')
    profile_image_url = google_user_data.get('picture', '')

    if not user:
        # If the user doesn't exist, create a new entry.
        cursor.execute('INSERT INTO user (name, email, password, token_balance, profile) VALUES (%s, %s, %s, %s, %s)',
                       (full_name, google_user_data['email'], '', 100, profile_image_url,))
        mysql.connection.commit()
        user_id = cursor.lastrowid
    else:
        # If the user already exists, update the name if it has changed.
        cursor.execute('UPDATE user SET name = %s WHERE email = %s',
                       (full_name, google_user_data['email'],))
        mysql.connection.commit()
        user_id = user['user_id']

    # Set the user's session data
    session['loggedin'] = True
    session['user_id'] = user_id
    session['name'] = full_name
    session['email'] = google_user_data['email']

    # Redirect to the feed or homepage after successful login
    return redirect(url_for('feed'))




#--------------------------User login--------------------------
@app.route("/login", methods=("GET", "POST"))
def login():

    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['email'] = user['email']
            return redirect(url_for('feed'))
        else:
            flash('Invalid email or password', 'error')

    return redirect(url_for('home'))



#--------------------------User registration--------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']
        token_balance = request.form['token_balance']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')  # Hash the password
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        account = cursor.fetchone()
        
        if account:
            flash('Account already exists!', 'error')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!', 'error')
        elif not userName or not password or not email:
            flash('Please fill out the form!', 'error')
        else:
            cursor.execute('INSERT INTO user (name, email, password, token_balance) VALUES (%s, %s, %s, %s)', (userName, email, hashed_password, token_balance,))
            mysql.connection.commit()

    return redirect(url_for('feed'))



#---------------Forget password page-----------------
@app.route('/forgot', methods =['GET', 'POST'])
def forgot():
    if 'login' in session:
        return redirect('/')

    if request.method == 'POST':
        email = request.form['email']
        token = str(uuid.uuid4())
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        result = cursor.execute('SELECT * FROM user WHERE email = % s', (email, ))

        if result > 0:
            data = cursor.fetchone()
            msg = Message(subject="Forgot password request", sender='aiinterf@gmail.com', recipients=[email])
            msg.body = render_template('sent.html', token=token, data=data)
            mail.send(msg)

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('UPDATE user SET token = % s WHERE email = % s', (token, email, ))
            mysql.connection.commit()
            cursor.close()
            mesage = 'Link already sent to your email..'
            return render_template('forgot.html', mesage = mesage)
        else:
            mesage = 'Email does not match..'
            return render_template('forgot.html', mesage = mesage)


    return render_template('forgot.html')


#-------------------------User reset password----------------------
@app.route('/reset/<token>', methods =['GET', 'POST'])
def reset(token):
    if 'login' in session:
        return redirect('/')

    if request.method == 'POST':
        password = request.form['password']
        c_password = request.form['c_password']
        token1 = str(uuid.uuid4())

        if password != c_password:
            mesage = 'Your password does not match'
            return render_template('reset.html', mesage = mesage)
        password = password

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE token = % s', (token, ))
        user = cursor.fetchone()

        if user:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('UPDATE user SET token = % s, password = % s WHERE token = % s', (token1, password, token, ))
            mysql.connection.commit()
            cursor.close()
            mesage = 'Your password successfully updated..'
            return render_template('login.html', mesage = mesage)
        else:
            mesage = 'Your token is invalid..'
            return render_template('reset.html', mesage = mesage)


    return render_template('reset.html')



#--------------------------User logout--------------------------
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('email', None)
    return redirect(url_for('home'))



#-------------------------Custom Error handling if 404--------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 400

#--------------------------Custom Error handling if 500--------------------------
@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500

#--------------terms and condition page-------------------

@app.route('/terms', methods=['GET', 'POST'])
def terms():

    return render_template('terms.html')


#------------------thank you page-----------------
@app.route('/thank_you', methods=['GET', 'POST'])
def thank_you():

    return render_template('thank.html')



if __name__ == "__main__":
    app.run()


