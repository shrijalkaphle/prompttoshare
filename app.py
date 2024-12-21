import os
os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"
import re
import threading
import time
import json
import base64
import boto3
import tempfile
import botocore
import random
import requests
import io 
import urllib.request
from dotenv import load_dotenv
import multiprocessing


import stripe

from flask import Flask, redirect, render_template, request, send_from_directory, url_for, session, jsonify, flash, Response, send_file, make_response
from flask_oauthlib.client import OAuth
from markupsafe import Markup
import unidecode
from werkzeug.utils import secure_filename
from openai import Completion
from datetime import datetime
from PIL import Image
from moviepy.editor import VideoFileClip
from io import BytesIO
from flask_socketio import SocketIO
from flask_cors import CORS

from flask_bcrypt import Bcrypt, check_password_hash

from flask_wtf.csrf import CSRFProtect

from flask_mysqldb import MySQL
from flask_mail import Mail, Message
import MySQLdb.cursors
import re
import uuid
from celery.result import AsyncResult
from helpers.jwt import authGuard
import tasks

from helpers.routes.admin import admin
from helpers.routes.user import user
from helpers.routes.auth import auth
from helpers.routes.post import post
from helpers.routes.openai import openai
from helpers.routes.search import search
from helpers.routes.payments import payments

from openai import OpenAI

app = Flask(__name__, static_url_path='/static')

app.add_url_rule('/.well-known/<path:filename>', endpoint='.well-known', view_func=app.send_static_file)

app.config['UPLOAD_FOLDER'] = 'static/temp_img'


# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Define the folder where you want to save the images
image_folder = os.path.join(os.getcwd(), "static/images")  # Change "images" to your desired folder name

# Create the image folder if it doesn't exist
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

# socketio = SocketIO(app)

# CORS(app, resources={r"/": {"origins": "https://yourtrusteddomain.com"}})
# socketio = SocketIO(app, cors_allowed_origins="https://yourtrusteddomain.com")

queue = multiprocessing.Queue()

bcrypt = Bcrypt(app)

app.secret_key = 'I%uI*&LuV4yX92ve'

# Facebook App Configurations
FB_APP_ID = '861161571799626'
FB_APP_SECRET = '6e00b8fcf9a25456dfc7ae77d8c161cb' 
FB_REDIRECT_URI = 'http://localhost:5000/facebook/callback'

oauth = OAuth(app)
CORS(app)

env_file_name = "env.yml"
load_dotenv(dotenv_path=env_file_name)

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
csrf.exempt(user)
csrf.exempt(admin)
csrf.exempt(auth)
csrf.exempt(post)
csrf.exempt(openai)
csrf.exempt(search)
csrf.exempt(payments)

# register routes
app.register_blueprint(admin, url_prefix='/api/admin')
app.register_blueprint(user, url_prefix='/api')
app.register_blueprint(auth, url_prefix='/api/auth')
app.register_blueprint(post, url_prefix='/api')
app.register_blueprint(openai, url_prefix='/api')
app.register_blueprint(search, url_prefix='/api')
app.register_blueprint(payments, url_prefix='/api')

# UPLOAD_FOLDER = 'static/upload_file'
# UPLOAD_PROFILE = 'static/upload_profile'

 
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'root'
# app.config['MYSQL_PASSWORD'] = ''
# app.config['MYSQL_DB'] = 'counselai'
# app.config['MYSQL_UNIX_SOCKET'] = '/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock'

app.config['MYSQL_HOST'] = 'us-cdbr-east-06.cleardb.net'
app.config['MYSQL_USER'] = 'b57d02d193bc19'
app.config['MYSQL_PASSWORD'] = 'a3f1503e'
app.config['MYSQL_DB'] = 'heroku_7e298305dcadd8d'
mysql = MySQL(app)

app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = '465'
app.config['MAIL_USE_SSL'] = 'True'
app.config['MAIL_USE_TSL'] = 'False'
app.config['MAIL_USERNAME'] = 'aiinterf@gmail.com'
app.config['MAIL_PASSWORD'] = 'xylatfxzephzrmjf'
mail = Mail(app)


# AWS S3 configuration
BUCKET_NAME = 'ai-interf-social'
TEMP_BUCKET_NAME = 'aiinterf-temp-file'

AWS_ACCESS_KEY_ID = '###############'
AWS_SECRET_ACCESS_KEY = 


from dotenv import load_dotenv 
load_dotenv()
openaiClient=OpenAI(
    api_key="###############################"
)
# openai.api_key = "###############################"
model_engine = 'gpt-3.5-turbo'

# Set the max number of characters per chunk
MAX_CHARS_PER_CHUNK = 500

# Set the words per minute for text streaming
WORDS_PER_MINUTE = 60

CUSTOM_STATIC_PATH=app.root_path + '/static/well-known/'


@app.route('/slufigy', methods=['GET'])
def slufigy():
    """
    Retrieves the last 10 posts from the 'feed' table in the MySQL database and updates their 'slug' field.

    Returns:
        str: A message indicating that the slugification process is done.

    Raises:
        MySQLdb.Error: If there is an error executing the SQL query.
    """
    connection = MySQLdb.connect(host="us-cdbr-east-06.cleardb.net", user="b57d02d193bc19", passwd="a3f1503e", db="heroku_7e298305dcadd8d")
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM feed ORDER BY id DESC LIMIT 10")
    feed = cursor.fetchall()
    for p in feed:
        text = unidecode.unidecode(p['title']).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str(int((p['created_at'] - datetime(1970, 1, 1)).total_seconds())) + '_' + slug
        cursor.execute("UPDATE feed SET slug = %s WHERE id = %s", (slug, p['id'],))
        connection.commit()

    return "Slufigy done";


@app.route('/api/upload/video', methods=['POST'])
@csrf.exempt
def uploadVideo():
    """
    Uploads a video file to the server and compresses it. The function is accessible via a POST request to the '/api/upload/video' endpoint.

    Returns:
        dict: A dictionary containing the S3 URL of the compressed video file and a unique token.

    Raises:
        None

    Example:
        POST /api/upload/video
        Request Body:
            file: The video file to be uploaded.

        Response:
            {
                "s3Url": "https://ai-interf-social.s3.amazonaws.com/compressed_video_filename.mp4",
                "token": "unique_token"
            }
    """
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    video = request.files.get('file')
    video_filename = 'original_' + secure_filename(video.filename)
    video.save(video_filename)
    compressed_filename = 'compressed_' + secure_filename(video.filename).split('.')[0] + '.mp4'
    token = uuid.uuid4().hex

    thread = threading.Thread(target=uploadVideoThread, args=(video_filename,compressed_filename,token ))
    thread.start()
    s3Url = f"https://ai-interf-social.s3.amazonaws.com/{compressed_filename}"
    return {"s3Url": s3Url, "token": token}


def uploadVideoThread(fileName, compressedFileName, token):
    """
    Uploads a video file to an S3 bucket and updates the corresponding entry in the database.

    Args:
        fileName (str): The name of the video file to be uploaded.
        compressedFileName (str): The name of the compressed video file to be saved.
        token (str): The unique token associated with the video entry in the database.

    Returns:
        None

    Raises:
        FileNotFoundError: If the original video file or the compressed video file does not exist.
        Exception: If there is an error during the upload process.

    """
    # upload file to s3
    video_clip = VideoFileClip(fileName)
    compressed_clip = video_clip.resize(height=480)
    compressed_clip.write_videofile(compressedFileName, codec='libx264', bitrate='500k')
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    print("uploading to s3")
    s3.upload_file(compressedFileName, BUCKET_NAME, compressedFileName)

    # delete temp files
    print("deleting temporary files")
    os.remove(fileName)
    os.remove(compressedFileName)

    # update database
    connection = MySQLdb.connect(host="us-cdbr-east-06.cleardb.net", user="b57d02d193bc19", passwd="a3f1503e", db="heroku_7e298305dcadd8d")
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM feed WHERE token = '" + token + "'")
    feed = cursor.fetchone()
    if feed:
        cursor.execute("UPDATE feed SET status = NULL, token = NULL WHERE id = %s", (feed['id'],))
        connection.commit()

    print('completed')


@app.route('/api/upload/image', methods=['POST'])
@csrf.exempt
def uploadImage():
    """
    Uploads an image file to an S3 bucket and returns the URL and token of the uploaded image.

    This function is a Flask route that handles POST requests to '/api/upload/image'. It expects a file named 'file' in the request form data. The function first checks if the request is authorized using the `authGuard` function. If the request is not authorized, it returns a JSON response with an 'error' key set to 'Unauthorized access'.

    If the request is authorized, the function retrieves the uploaded image file from the request form data using `request.files.get('file')`. It then generates a secure filename for the image using `secure_filename` and saves the image file with the generated filename.

    The function generates a unique token using `uuid.uuid4().hex` and starts a new thread to upload the image file to an S3 bucket using the `uploadImageThread` function. The thread is passed the filename and the token as arguments.

    Finally, the function constructs the URL of the uploaded image in the S3 bucket using the filename and returns a JSON response with the 's3Url' key set to the URL and the 'token' key set to the generated token.

    Returns:
        A JSON response containing the 's3Url' key set to the URL of the uploaded image and the 'token' key set to the generated token.

    Raises:
        None
    """
    if not authGuard(request):
        return {'error': 'Unauthorized access'};

    image = request.files.get('file')
    filename = secure_filename(image.filename)
    image.save(filename)
    token = uuid.uuid4().hex

    thread = threading.Thread(target=uploadImageThread, args=(filename,token ))
    thread.start()
    s3Url = f"https://ai-interf-social.s3.amazonaws.com/{filename}"
    return {"s3Url": s3Url, "token": token}


def uploadImageThread(fileName, token):
    """
    Uploads an image to an AWS S3 bucket and performs some image processing operations.

    Args:
        fileName (str): The name of the image file to be uploaded.
        token (str): A unique identifier for the image.

    Returns:
        None

    Raises:
        None

    This function takes the name of an image file and a token as input. It opens the image file in binary mode and reads its contents. It then checks if the image mode is 'RGBA' and converts it to 'RGB' if necessary. Next, it calculates new dimensions for 50% compression by resizing the image. The image is then compressed to the target size using the `compress_image` function.

    The function creates an S3 client using the AWS access key and secret access key, and uploads the compressed image data to the S3 bucket using the `upload_fileobj` method.
    """
    with open(fileName, 'rb') as file:
        image = Image.open(file)
        
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        # Calculate new dimensions for 50% compression
        width, height = image.size
        new_width = int(width * 0.5)
        new_height = int(height * 0.5)

        # Resize the image
        resized_image = image.resize((new_width, new_height))
        compressed_image_data = compress_image(resized_image, target_size_kb=50)

        s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        print("uploading to s3")
        s3.upload_fileobj(compressed_image_data, BUCKET_NAME, fileName, ExtraArgs={'ContentType': 'image/jpeg'})
        print('uploaded')

    print("deleting temporary files")
    os.remove(fileName)
    # update database
    connection = MySQLdb.connect(host="us-cdbr-east-06.cleardb.net", user="b57d02d193bc19", passwd="a3f1503e", db="heroku_7e298305dcadd8d")
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM feed WHERE token = '" + token + "'")
    feed = cursor.fetchone()
    if feed:
        cursor.execute("UPDATE feed SET status = NULL, token = NULL WHERE id = %s", (feed['id'],))
        connection.commit()

    print('completed')
    pass


@app.route('/post/<slug>', methods=['GET'])
def viewSinglePost(slug):
    """
    Retrieves a single post from the database based on the provided slug and renders it in a template.

    Parameters:
        slug (str): The unique identifier of the post.

    Returns:
        str: The rendered HTML template of the single post page.
    """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if session.get('loggedin'):
        user_id = session['user_id']
        cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
    else:
        user_id = None
        user = None
    
    cursor.execute("SELECT * FROM feed WHERE slug = %s", (slug,))
    feed = cursor.fetchone()
    cursor.execute("SELECT name, profile, user_id FROM user WHERE user_id = %s", (feed['user_id'],))
    feed['user'] = cursor.fetchone()
    cursor.execute("SELECT comment.*, user.name, user.profile, user.user_id FROM comment LEFT JOIN user ON comment.user_id = user.user_id WHERE post_id = %s", (feed['id'],))
    feed['comment']= cursor.fetchall()
    cursor.execute("SELECT count(*) as total FROM likes WHERE post_id = %s", (feed['id'],))
    feed['likes']= cursor.fetchone()['total']
    cursor.execute("SELECT count(*) as total FROM trophy WHERE post_id = %s", (feed['id'],))
    feed['trophy']= cursor.fetchone()['total']
    del feed['user_id']

    if user_id:
        cursor.execute("SELECT * FROM likes WHERE user_id = %s AND post_id = %s", (user_id, feed['id']))
        feed['is_liked'] = True if cursor.fetchone() else False

        cursor.execute("SELECT * FROM trophy WHERE user_id = %s AND post_id = %s", (user_id, feed['id']))
        feed['is_trophy'] = True if cursor.fetchone() else False
    else:
        feed['is_liked'] = False
        feed['is_trophy'] = False


    feed['chunk'] = feed['chunk'].replace("\n", "<br/>")
    return render_template('singlePost.html', feed=feed, user=user)

@app.route('/create-checkout-session', methods=['POST'])
def checkoutSession():
    """
    Creates a checkout session for a user to make a payment.

    This function is an endpoint for the '/create-checkout-session' route. It is triggered when a POST request is made to this route. The function creates a checkout session using the Stripe API to allow the user to make a payment.

    Parameters:
    - None

    Returns:
    - A redirect response to the Stripe checkout session URL.

    Raises:
    - None
    """


    amount = request.form.get('price')
    stripe.api_key = '########################################'

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('INSERT INTO pending_order (user_id, price, qty, payment_type, payment_intent_id, created_at) VALUES (%s,%s,%s,%s,%s, NOW())', (user_id, amount, (int(amount) * 96), 'N.A', 'N.A',))
    mysql.connection.commit()

    cursor.execute('SELECT * from pending_order ORDER BY id DESC LIMIT 1')
    order = cursor.fetchone()
    print(order)

    stripeSession =  stripe.checkout.Session.create(
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'P2S Coins',
                },
                'unit_amount': int(amount) * 100,
            },
            'quantity': 1,
        }],
        mode='payment',
        cancel_url='https://www.prompttoshare.com/stripeResponse/cancel?session='+str(order['id']),
        payment_method_types=['card'],
    )
    
    return redirect(stripeSession.url, code=303)


@app.route('/stripeResponse/<responseType>', methods=['GET'])
def stripeResponse(responseType):
    """
    This function handles the response from Stripe after a payment has been processed. It takes in a 
    responseType parameter which can be either 'cancel' or 'success'. If the responseType is 'cancel', 
    the function deletes the corresponding order from the 'pending_order' table and redirects the user 
    to the 'tokenbuy' page. If the responseType is 'success', the function retrieves the order details 
    from the 'pending_order' table, updates the user's token balance, inserts the order details into 
    the 'orders' table, and deletes the order from the 'pending_order' table. The function then commits 
    the changes to the database and redirects the user to the 'home' page. If the responseType is neither 
    'cancel' nor 'success', the function returns a dictionary with the responseType as the key.
    
    Parameters:
    responseType (str): The type of response from Stripe ('cancel' or 'success').
    
    Returns:
    dict or redirect: If the responseType is 'cancel', returns a redirect to the 'tokenbuy' page. If 
    the responseType is 'success', returns a redirect to the 'home' page. If the responseType is neither 
    'cancel' nor 'success', returns a dictionary with the responseType as the key.
    """
    orderId = request.args.get('session')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if responseType == 'cancel':
        cursor.execute('DELETE from pending_order WHERE id = '+str(orderId))
        mysql.connection.commit()
        return redirect(url_for('tokenbuy'))
    if responseType == 'success':
        cursor.execute('SELECT * from pending_order WHERE id = '+str(orderId))
        order = cursor.fetchone()

        cursor.execute('SELECT token_balance FROM user WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        current_balance = result['token_balance']

        updated_balance = int(order['qty']) + current_balance
        cursor.execute('UPDATE user SET token_balance = %s WHERE user_id = %s', (updated_balance, user_id))

        cursor.execute('INSERT INTO orders (user_id, price, qty, payment_type, created_at) VALUES (%s, %s, %s,%s, NOW())', (user_id, order['price'], order['qty'], 'card'))
        cursor.execute('DELETE from pending_order WHERE id = '+str(order['id']))
        mysql.connection.commit()
        return redirect(url_for('home'))
    return {
        "responseType" : responseType
    }

@app.errorhandler(400)
def handle_csrf_error(e):
    """
    Handle CSRF error by redirecting the user to the previous URL.

    Parameters:
        e (Exception): The exception object representing the CSRF error.

    Returns:
        redirect: A redirect to the previous URL.
    """
    previous_url = request.referrer
    return redirect(previous_url)

@app.route('/.well-known/<filename>')
def wellKnownRoute(filename):
    """
        Route handler for serving files from the .well-known directory.

        Args:
            filename (str): The name of the file to be served.

        Returns:
            flask.Response: The response object containing the file content.

        Raises:
            None

        This route handler is used to serve files from the .well-known directory. It takes a filename as a parameter
        and uses the send_from_directory function from Flask to send the file content as a response. The file is served
        conditionally based on the If-Modified-Since header.
    """
    
    return send_from_directory(CUSTOM_STATIC_PATH, filename, conditional=True)

# Define a route to check the task status and get the result
@app.route('/tasks/', methods=['GET'])
def run_task():
    """
    Route handler for running a task.

    This function is responsible for running a task asynchronously using the Celery task queue. It takes no parameters.

    Returns:
        flask.Response: The response object containing the task ID, status, and result.

    Raises:
        None

    This route handler is used to trigger the execution of the `add_numbers` task asynchronously. It takes two integers as arguments, `1` and `2`, and applies them to the task using the `apply_async` method. The task is then executed asynchronously and the result is returned in the response.
    """
    result = tasks.add_numbers.apply_async(args=[1, 2])
    return jsonify(result.id, result.status, result.result)

# Define a route to check the task status and get the result
@app.route('/status/<task_id>', methods=['GET'])
def check_task_status(task_id):
    """
    Route handler for checking the status of a task.

    This function is responsible for checking the status of a task and retrieving its result. It takes a task ID as a parameter and returns the task status and result.

    Parameters:
        task_id (str): The ID of the task to check.

    Returns:
        dict: A dictionary containing the task status, result value, name of the result file, and download URL for the result file.

    Raises:
        None

    This route handler is used to check the status of a task and retrieve its result. It queries the Celery task queue to get the status of the task with the given ID. If the task is in the 'SUCCESS' state, it retrieves the result and performs the following steps:
    1. Generates a unique filename for the result file.
    2. Retrieves the URL of the result image.
    3. Downloads the image from the URL using the requests library.
    4. Opens the downloaded image using the Pillow library.
    5. Compresses the image while trying to maintain quality and target size.
    6. Saves the compressed image to a temporary file.
    7. Uploads the temporary file to an S3 bucket using the boto3 library.
    8. Deletes the temporary file.
    9. Returns a dictionary containing the task status, result value, name of the result file, and download URL for the result file.

    If the task is not in the 'SUCCESS' state, it returns a JSON response with an error message.

    Note: This function uses the Celery task queue and the boto3 library for interacting with the task queue and the S3 bucket, respectively.
    """
    while True:  
        result = AsyncResult(id=f"{task_id}", app=tasks.celery)
        if result.status == 'SUCCESS':
            print(result.result)
            # save image to s3
            filename = uuid.uuid4().hex + '.png'
            image_url = result.result['data'][0]['url']
            response = requests.get(image_url)
            
            if response.status_code == 200:
                # Open the downloaded image using Pillow
                image = Image.open(io.BytesIO(response.content))

                # Compress the image while trying to maintain quality and target size
                max_size_kb = 50  # Target size in KB
                quality = 95  # Initial quality
                buffer = io.BytesIO()
                while True:
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=quality)
                    if buffer.getbuffer().nbytes < max_size_kb * 1024 or quality <= 10:
                        break
                    quality -= 5

                # Save the compressed image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                    temp_file.write(buffer.getvalue())

                s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
                image_filename = secure_filename(filename)

                # Upload the temporary file to S3
                s3.upload_file(temp_file.name, TEMP_BUCKET_NAME, image_filename)

                # Delete the temporary file
                os.remove(temp_file.name)
            else:
                return jsonify({'error': 'Failed to download the image from the URL'})
            return {
                "ready": result.status,
                "value": result.result,
                "name": filename,
                "download": f"https://{TEMP_BUCKET_NAME}.s3.amazonaws.com/{filename}"
            }
        time.sleep(1)



#----------Admin Page section-------
@app.route("/ai-interf-social-admin", methods=("GET", "POST"))
def admin():
    """
    This function handles the admin page for the AI Interf Social website. It checks if the user is logged in, and if so, retrieves information about the posts, users, orders, withdrawals, notices, prompts, notifications, reports, promoted posts, and security settings. If the user is not logged in, it redirects them to the home page.

    Parameters:
    None

    Returns:
    If the user is logged in and is the admin, it returns the rendered admin.html template with the necessary data. If the user is not logged in or is not the admin, it redirects them to the home page.
    """
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

            formatted_trophy_count = str(total_trophies).zfill(2)

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

        cursor.execute('SELECT report.*, user.name, user.email FROM report JOIN user WHERE user.user_id = report.user_id ORDER BY report.id DESC')
        report = cursor.fetchall()

        cursor.execute('SELECT * FROM promoted ORDER BY promoted.id DESC')
        promoted = cursor.fetchall()

        cursor.execute('SELECT * FROM feed ORDER BY feed.id DESC')
        feed = cursor.fetchall()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
        notification_count = cursor.fetchone()['notification_count']

        # Retrieve the notifications for the user
        cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
        notifications = cursor.fetchall()
        
        # Retrieve the security settings
        cursor.execute('SELECT * FROM security')
        security = cursor.fetchone()

        cursor.execute('SELECT * FROM user WHERE user_id = %s', (session.get('user_id'),))
        current_user = cursor.fetchone()

        return render_template("admin.html", users=users, orders=orders, withdraw=withdraw, notice=notice, prompt=prompt, notifications=notifications, user=user, 
            notification_count=notification_count, total_likes=total_likes, total_trophies=formatted_trophy_count, report=report, promoted=promoted, feed=feed, security=security,current_user=current_user)
    else:
        return redirect(url_for('feed'))



@app.route("/update_security/<int:security_id>", methods=["POST"])
def update_security(security_id):
    profile_rating = request.form.get("profile_rating")
    problem_report = request.form.get("problem_report")
    post = request.form.get("post")
    generate = request.form.get("generate")

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE security SET profile_rating = %s, problem_report = %s, post = %s, generate = %s WHERE id = %s', (profile_rating, problem_report, post, generate, security_id))
    mysql.connection.commit()

    print(request)

    return redirect(url_for('admin'))


#----------------feed delete section---------------------------
@app.route("/delete_feed/<int:feed_id>", methods=("POST",))
def delete_feed(feed_id):
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    # Post found and belongs to the logged-in user, delete it
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM feed WHERE id = %s', (feed_id,))
    mysql.connection.commit()

    flash('Post deleted successfully!', 'success')

    return redirect(url_for('admin'))



#----------------user status edit section---------------------------
@app.route('/useredit/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    """
    Edit the status of a user.

    Parameters:
        user_id (int): The ID of the user to edit.

    Returns:
        redirect: A redirect to the 'admin' route.

    Raises:
        None
    """
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    status = request.form.get('status')

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE user SET status = %s WHERE user_id = %s', (status, user_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))


#----------------withdraw edit section---------------------------
@app.route('/widedit/<wid_id>', methods=['GET', 'POST'])
def edit_wid(wid_id):
    """
    Edit the withdrawal information for a specific user.

    Parameters:
        wid_id (int): The ID of the withdrawal to edit.

    Returns:
        redirect: A redirect to the 'admin' route.

    Raises:
        None
    """
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    sender_account = request.form.get('sender_account')
    sender_receipt = request.form.get('sender_receipt')
    status = request.form.get('status')

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE withdraw SET sender_account = %s, sender_receipt = %s, status = %s WHERE id = %s', (sender_account, sender_receipt, status, wid_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('admin'))


#----------------prompt add section---------------------------
@app.route("/addprompt", methods=['POST'])
def add_prompt():
    """
    Adds a new prompt to the database.

    This route is used to add a new prompt to the database. It is accessible via a POST request to the "/addprompt" route.

    Parameters:
        None

    Returns:
        redirect: A redirect to the 'admin' route.

    Raises:
        None
    """
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
    """
    Updates the name of a prompt in the database.

    Args:
        prompt_id (int): The ID of the prompt to be updated.

    Returns:
        redirect: A redirect to the 'admin' route.

    Raises:
        None
    """
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
    """
    Deletes a prompt from the database.

    Parameters:
        prompt_id (int): The ID of the prompt to be deleted.

    Returns:
        redirect: A redirect to the 'admin' route.

    Raises:
        None
    """
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    # Post found and belongs to the logged-in user, delete it
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM prompt WHERE id = %s', (prompt_id,))
    mysql.connection.commit()

    flash('Post deleted successfully!', 'success')

    return redirect(url_for('admin'))


#----------------notice add section---------------------------
@app.route("/addnotice", methods=['POST'])
def add_notice():
    """
    Adds a new notice to the database.

    This route handles the POST request to '/addnotice'. It expects a form field named 'name' in the request.

    Parameters:
    - None

    Returns:
    - A redirect to the 'admin' route.

    Raises:
    - None
    """
    name = request.form.get('name')

    if request.method == "POST":
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO notice (name, created_at) VALUES (%s, NOW())', (name,))
        mysql.connection.commit()


        return redirect(url_for('admin'))


#---------------notice edit page -------------------------
@app.route('/noticeedit/<notice_id>', methods=['GET', 'POST'])
def edit_notice(notice_id):
    """
    Edit a notice with the given notice_id.

    Parameters:
    - notice_id (int): The ID of the notice to be edited.

    Returns:
    - A redirect to the 'admin' route.

    Raises:
    - None
    """
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
    """
    Deletes a notice from the database.

    Parameters:
    - notice_id (int): The ID of the notice to be deleted.

    Returns:
    - A redirect to the 'admin' route.

    Raises:
    - None
    """
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    # Post found and belongs to the logged-in user, delete it
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM notice WHERE id = %s', (notice_id,))
    mysql.connection.commit()

    return redirect(url_for('admin'))


#----------------promoted add section---------------------------
@app.route("/addpromoted", methods=['POST'])
def add_promoted():
    """
    Add a new promoted item to the database.

    This route handles the POST request to add a new promoted item to the database. It requires the user to be logged in.

    Parameters:
    - None

    Returns:
    - A redirect to the 'admin' route.

    Raises:
    - None
    """
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    name = request.form.get('name')
    link = request.form.get('link')
    file = request.files['image']

    if request.method == "POST":

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
        cursor.execute('INSERT INTO promoted (name, link, image) VALUES (%s, %s, %s)', (name, link, file_path))
        mysql.connection.commit()

        return redirect(url_for('admin'))


#---------------promoted edit page -------------------------
@app.route('/promotededit/<promote_id>', methods=['GET', 'POST'])
def edit_promoted(promote_id):
    """
    Edit a promoted item with the given ID.

    Parameters:
        promote_id (str): The ID of the promoted item to edit.

    Returns:
        redirect: A redirect to the 'admin' page if the user is logged in.

    Raises:
        None

    Description:
        This function is a route handler for the '/promotededit/<promote_id>' URL. It checks if the user is logged in, and if not, redirects them to the home page. 

        If the user is logged in, it retrieves the 'name' and 'link' values from the request form, and the 'image' file from the request files. It then executes an SQL UPDATE query to update the promoted item in the database with the new values.

        After the update, it commits the changes to the database and closes the cursor. Finally, it redirects the user to the 'admin' page.

        Note: This function assumes that the 'loggedin' session variable is set to True if the user is logged in.

    """
    if not session.get('loggedin'):
        return redirect(url_for('home'))

    name = request.form.get('name')
    link = request.form.get('link')
    file = request.files['image']

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE promoted SET name = %s, link = %s, image = %s WHERE id = %s', (name, link, file, promote_id))
    mysql.connection.commit()
    cursor.close()


    return redirect(url_for('admin'))


#----------------promoted delete section---------------------------
@app.route("/delete_promoted/<int:promote_id>", methods=("POST",))
def delete_promoted(promote_id):
    """
    Deletes a promoted item from the database.

    Parameters:
        promote_id (int): The ID of the promoted item to be deleted.

    Returns:
        flask.Response: A redirect response to the 'admin' page.

    Raises:
        None

    Notes:
        - This route is accessed via a POST request to '/delete_promoted/<int:promote_id>'.
        - The function checks if the user is logged in by checking the 'loggedin' session variable.
        - If the user is not logged in, they are redirected to the 'home' page.
        - If the user is logged in, the function deletes the promoted item with the specified ID from the database.
        - After deleting the item, the function commits the changes and closes the cursor.
        - The function then redirects the user to the 'admin' page.

    """
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    # Post found and belongs to the logged-in user, delete it
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM promoted WHERE id = %s', (promote_id,))
    mysql.connection.commit()

    return redirect(url_for('admin'))

#-----------Home Page-----------------
@app.route("/", methods=("GET", "POST"))
def home():
    """
    This function is the route handler for the root URL ("/") of the application.
    It handles both GET and POST requests.

    Parameters:
    None

    Returns:
    - If the user is logged in, it redirects the user to the 'feed' page.
    - If the user is not logged in, it retrieves the latest 18 posts from the database and their associated information such as the number of comments, likes, and trophies.
    - It then renders the 'home.html' template with the retrieved posts and prompts.

    Notes:
    - This function uses the Flask framework to handle the routing.
    - The session variable 'loggedin' is checked to determine if the user is logged in.
    - The MySQL database is queried to retrieve the posts and their associated information.
    - The retrieved posts are stored in a list of dictionaries and passed to the 'home.html' template.
    - The prompts are also retrieved from the database and passed to the template.
    """
    if session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('feed'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM feed ORDER BY feed.id DESC LIMIT 18')
    post = cursor.fetchall()

    post_array = []

    for p in post:
        post_id = p['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        # print("Comment Count:", comment_count['comment_count'])

        
        # Get the number of likes for the post/
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
            'chunk': p['chunk'].strip().split('\n\n') if p['chunk'] else '',
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
    """
    Route for the newsfeed page.

    This function handles the GET and POST requests to the '/newsfeed' route.
    If the user is logged in, it redirects to the 'feed' route.
    Otherwise, it retrieves the latest posts from the 'feed' table in the database.
    For each post, it retrieves the number of comments, likes, and trophies associated with it.
    It also retrieves the username and profile of the user who created the post.
    Finally, it renders the 'newsfeed.html' template with the retrieved post data.

    Parameters:
        None

    Returns:
        A rendered HTML template 'newsfeed.html' with the retrieved post data.

    Raises:
        None
    """
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
            'chunk': p['chunk'].strip().split('\n\n') if p['chunk'] else '',
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

@app.route("/feed_more", methods=["GET"])
def load_more():
    """
    Route for loading more posts in the feed.

    This route is responsible for loading more posts in the feed when the user scrolls down. It checks if the user is logged in and returns an error if not. It then retrieves the user's ID from the session.

    The function executes a SQL query to select all posts from the feed table joined with the user table, ordering the results by the post ID in descending order. It fetches all the results and stores them in the `post` variable.

    For each post in `post`, the function retrieves the post ID and performs the following operations:
    - Retrieves the number of comments for the post using a SQL query.
    - Retrieves the number of likes for the post using a SQL query.
    - Retrieves the number of trophies for the post using a SQL query.
    - Checks if the user has liked the trophy for the post using a SQL query.

    The retrieved data is stored in the `postObj` dictionary with the following keys:
    - id: The ID of the post.
    - title: The title of the post.
    - chunk: The content of the post, split into paragraphs.
    - category: The category of the post.
    - file: The file associated with the post.
    - tool: The tool associated with the post.
    - name: The name of the user who created the post.
    - profile: The profile picture of the user who created the post.
    - comment_count: The number of comments associated with the post.
    - like_count: The number of likes associated with the post.
    - trophy_count: The number of trophies associated with the post.
    - has_liked_trophy: A boolean indicating whether the user has liked the trophy for the post.

    Finally, the `postObj` dictionary is appended to the `post_array` list.
    """
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return jsonify({'error': 'User not logged in'}), 401
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()
    post_array = []

    for p in post:
        post_id = p['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()

        # Check if the user has liked the trophy for this post
        cursor.execute('SELECT COUNT(*) AS liked_trophy FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, user_id))
        liked_trophy = cursor.fetchone()

        postObj = {
            'id': p['id'],
            'title': p['title'],
            'chunk': p['chunk'].strip().split('\n\n') if p['chunk'] else '',
            'user_id': p['user_id'],
            'category': p['category'],
            'file': p['file'],
            'name': p['name'],
            'profile': p['profile'],
            'tool': p['tool'],
            'created_at': p['created_at'],
            'comment_count': comment_count['comment_count'],
            'like_count': like_count['like_count'],
            'trophy_count': trophy_count['trophy_count'],
            'liked_trophy': liked_trophy['liked_trophy'],



        }


        post_array.append(postObj)


    sorted_by_latest = sorted(post_array, key=lambda x: x['created_at'], reverse=True)
    sorted_by_highest_awarded = sorted(post_array, key=lambda x: (-x['like_count'], -x['trophy_count']))

    latest_2_posts = sorted_by_latest[0:2]
    highest_awarded_3_posts = sorted_by_highest_awarded[0:3]
    latest_5_posts = sorted_by_latest[2:7]
    highest_awarded_7_posts = sorted_by_highest_awarded[3:10]
    latest_15_posts = sorted_by_latest[8:23]

    filtered_posts = latest_2_posts + highest_awarded_3_posts + latest_5_posts + highest_awarded_7_posts + latest_15_posts

    return jsonify(filtered_posts);
    

#-------------NewsFeed Section----------------
@app.route("/feed", methods=("GET", "POST"))
def feed():
    """
    Renders the feed page for authenticated users.
    
    Retrieves the user's posts, user's own posts, and the number of likes and trophies for each post.
    Calculates the total number of likes and trophies for all posts.
    Sorts the posts based on like_count and trophy_count in descending order.
    Sorts the posts based on latest post.
    Retrieves the user's history, user's profile, user's notifications, and user's ratings.
    Retrieves the number of followed users, notices, prompts, and users.
    Retrieves the number of posts made today and the remaining post limit.
    Retrieves the number of generates made today and the remaining generate limit.
    Calculates the average rating for the user's profile.
    Retrieves the number of users who have rated the profile.
    Retrieves the number of users who have liked and received trophies.

    Returns:
        The rendered HTML template for the feed page.

    Raises:
        Exception: If the user is not logged in.
    """
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    user_id = session['user_id']
    post_array = []
    comment = []

    total_likes = 0
    total_trophies = 0

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id WHERE feed.user_id NOT IN (SELECT blocked_user_id FROM blocked_user WHERE user_id = %s) AND feed.deleted_at IS NULL AND feed.status IS NULL ORDER BY feed.id DESC', (user_id,))
    post = cursor.fetchall()

    

    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id WHERE user.user_id = %s ORDER BY feed.id DESC', (user_id,))
    user_post = cursor.fetchall()
    
    for p in user_post:
        post_id = p['id']
        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()
        total_likes += like_count['like_count']

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()
        total_trophies += trophy_count['trophy_count']

    processed_posts = []

    for p in post:
        post_id = p['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()

        # Check if the user has liked the trophy for this post
        cursor.execute('SELECT COUNT(*) AS liked_trophy FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, user_id))
        liked_trophy = cursor.fetchone()

        # cursor.execute('SELECT comment.*, user.name, user.profile FROM comment JOIN user ON comment.user_id = user.user_id WHERE comment.post_id = %s', (str(post_id)))
        cursor.execute('SELECT comment.*, user.name, user.profile FROM comment LEFT JOIN user ON comment.user_id = user.user_id WHERE post_id = %s', (post_id,))
        comment = cursor.fetchall()

        postObj = {
            'id': p['id'],
            'title': p['title'],
            'chunk': p['chunk'].strip().split('\n\n') if p['chunk'] else '',
            'user_id': p['user_id'],
            'category': p['category'],
            'file': p['file'],
            'name': p['name'],
            'profile': p['profile'],
            'tool': p['tool'],
            'created_at': p['created_at'],
            'comment_count': comment_count['comment_count'],
            'like_count': like_count['like_count'],
            'trophy_count': trophy_count['trophy_count'],
            'liked_trophy': liked_trophy['liked_trophy'],
            'comment': comment
        }


        post_array.append(postObj)

    # Sort the posts based on like_count and trophy_count in descending order
    limited_sorted_posts = sorted(post_array, key=lambda x: (-x['like_count'], -x['trophy_count']))
    sorted_posts = limited_sorted_posts[:3]
    sorted_posts_4_to_10 = limited_sorted_posts[3:10]

    # Sort the posts based on latest post
    limit_latest_post= sorted(post_array, key=lambda x: x['created_at'], reverse=True)
    latest_post = limit_latest_post[:5]
    latest_post_5_to_15 = limit_latest_post[5:15]

    #show history of each user
    cursor.execute('SELECT * FROM history WHERE user_id = %s AND deleted_at IS NULL ORDER BY id DESC', (user_id,))
    history = cursor.fetchall() 

    # getting each user 
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
    notification_count = cursor.fetchone()['notification_count']


    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
    # cursor.execute('SELECT * FROM notification WHERE user_id = %s ORDER BY id DESC', (user_id,))
    notifications = cursor.fetchall()

    # Get all ratings for the profile
    cursor.execute('SELECT rating_value FROM profile_rating WHERE profile_id = %s', (user_id,))
    ratings = cursor.fetchall()
    has_rated = bool(ratings)

    # Calculate the count of unique users who have rated the profile
    cursor.execute('SELECT COUNT(DISTINCT user_id) AS users_rated_count FROM profile_rating WHERE profile_id = %s', (user_id,))
    users_rated_count = cursor.fetchone()['users_rated_count']

    # post limit calculator
    cursor.execute('SELECT * FROM security')
    security = cursor.fetchone()
    post_limit = security['post']
    generate_limit = security['generate']
    
    # Calculate the count of posts made today
    today_post_count = 0
    cursor.execute('SELECT * FROM feed WHERE user_id = %s', (user_id,))
    user_post = cursor.fetchall()
    for post in user_post:
        if post['created_at'].date() == datetime.now().date():
            today_post_count += 1
        
    # calculate remaining post limit
    remaining_post_limit = post_limit - today_post_count
    
    # Calculate the count of generate made today
    today_generate_count = 0
    cursor.execute('SELECT * FROM history WHERE user_id = %s AND deleted_at IS NULL', (user_id,))
    user_generate = cursor.fetchall()
    for generate in user_generate:
        if generate['created_at'].date() == datetime.now().date():
            today_generate_count += 1
        
    # calculate remaining generate limit
    remaining_generate_limit = generate_limit - today_generate_count

    # Calculate the average rating
    if ratings:
        total_ratings = len(ratings)
        sum_ratings = sum(int(rating['rating_value']) for rating in ratings)
        average_rating = sum_ratings / total_ratings
        average_rating = round(average_rating, 1)  # Round to one decimal place
    else:
        average_rating = None

    

    #Get the number of followed user
    cursor.execute('SELECT COUNT(*) AS follower_count FROM follows WHERE follower_id = %s', (user_id,))
    follower_count = cursor.fetchone()['follower_count']

    #show notice from admin 
    cursor.execute('SELECT * FROM notice ORDER BY notice.id DESC LIMIT 5')
    notice = cursor.fetchall()

    #show prompts from admin in generate
    cursor.execute('SELECT * FROM prompt ORDER BY prompt.id')
    prompts = cursor.fetchall()

    #get all user
    cursor.execute('SELECT * FROM user ORDER BY user.user_id')
    users = cursor.fetchall()


    trophy_user_post = get_liked_posts_for_user(user_id)

    #show user reward
    cursor.execute('SELECT u.user_id, u.name, COUNT(l.post_id) AS total_likes FROM user u LEFT JOIN feed f ON u.user_id = f.user_id LEFT JOIN likes l ON f.id = l.post_id GROUP BY u.user_id, u.name;')
    user_like = cursor.fetchall()

    #show user trophy
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


    # Calculate the total number of users
    total_users = len(sorted_combined_data)

    # Calculate the desired number of users in the 1st percentile based on the total number of users
    desired_users_in_percentile = total_users // 10

    user_categories = {percentile: [] for percentile in range(1, 11)}

    # Separate users with 0 likes and trophies
    users_with_zero_rank = [user for user in sorted_combined_data if user['total_rank'] == 0]

    # Place users with 0 rank in the 0th percentile
    user_categories[0] = users_with_zero_rank

    # Assign users to percentiles based on their actual rank
    # for idx, user_data in enumerate(sorted_combined_data):
    #     if user_data['total_rank'] != 0:
    #         # Calculate percentile dynamically in reverse (1 being the lowest)
    #         percentile = 10 - (idx * 10) // total_users
    #         user_categories[percentile].append(user_data)

    # Assign users to percentiles based on their actual rank
    users_without_zero_rank = [user for user in sorted_combined_data if user['total_rank'] != 0]
    total_users = len(users_without_zero_rank)
    previous_end = 0
    for i in range (0,10):
        # calculate index based on percentile
        start_index = previous_end
        end_index = int(total_users * (i+1) / 10)

        # check if start and end endex are the same
        if start_index == end_index:
            end_index += 1
        # print(start_index,end_index)
        user_categories[10-i] = users_without_zero_rank[start_index:end_index]
        previous_end = end_index


    cursor.execute('SELECT * FROM promoted ORDER BY promoted.id DESC')
    promoted = cursor.fetchall()

    sorted_by_latest = sorted(post_array, key=lambda x: x['created_at'], reverse=True)
    sorted_by_highest_awarded = sorted(post_array, key=lambda x: (-x['like_count'], -x['trophy_count']))

    latest_2_posts = sorted_by_latest[0:2]
    highest_awarded_3_posts = sorted_by_highest_awarded[0:3]
    latest_5_posts = sorted_by_latest[2:7]
    highest_awarded_7_posts = sorted_by_highest_awarded[3:10]
    latest_15_posts = sorted_by_latest[8:23]

    filtered_posts = latest_2_posts + highest_awarded_3_posts + latest_5_posts + highest_awarded_7_posts + latest_15_posts


    cursor.execute('SELECT * FROM user WHERE user_id = %s', (session.get('user_id'),))
    current_user = cursor.fetchone()

    return render_template("feed.html", posts=post_array, post=sorted_posts, sorted_posts_4_to_10=sorted_posts_4_to_10, latest_post_5_to_15=latest_post_5_to_15, latest_post=latest_post, 
        video_post=post_array, history=history, notifications=notifications, user=user, users=users, notification_count=notification_count,
        average_rating=average_rating, total_likes=total_likes, total_trophies=total_trophies,follower_count=follower_count, notice=notice, prompts=prompts, user_like=user_like,
        user_trophy=user_trophy, rank=sorted_combined_data, trophy_user_post=trophy_user_post, user_categories=user_categories, promoted=promoted, users_rated_count=users_rated_count, remaining_post_limit=remaining_post_limit,
        remaining_generate_limit=remaining_generate_limit, filtered_posts = filtered_posts,current_user=current_user)



def get_liked_posts_for_user(user_id):
    """
    Retrieves the list of post IDs that the user with the given `user_id` has liked.

    Parameters:
        user_id (int): The ID of the user.

    Returns:
        List[int]: A list of post IDs that the user has liked.

    Raises:
        None

    Notes:
        - The function executes a SQL query to retrieve the post IDs from the `trophy` table
          where the `user_id` matches the given `user_id`.
        - The function uses a cursor to execute the query and fetch the results.
        - The function returns a list of post IDs that the user has liked.
    """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT post_id FROM trophy WHERE user_id = %s', (user_id,))
    trophy_user_post = [row['post_id'] for row in cursor.fetchall()]
    cursor.close()
    return trophy_user_post






#---------------feed search top nav -------------------------
@app.route('/api/users', methods=['GET'])
def get_users():
    """
    Retrieves a list of users based on a search query.

    This function is an API endpoint that handles GET requests to '/api/users'. It takes a query parameter 'q' which
    represents the search query. The function retrieves a list of users from the 'user' table in the database based on
    the search query. The search query is case-insensitive and is matched against the 'name' column of the 'user' table.

    Parameters:
        None

    Returns:
        A JSON response containing a list of dictionaries. Each dictionary represents a user and contains the
        following keys:
        - 'user_id' (int): The ID of the user.
        - 'name' (str): The name of the user.

    Raises:
        None

    Notes:
        - The function executes a SQL query to retrieve the user IDs and names from the 'user' table where the
          'user_id' is not in the 'blocked_user_id' column of the 'blocked_user' table and the 'name' column matches
          the search query.
        - The function uses the 'session' object to get the current user's ID.
        - The function returns an empty JSON response if the search query is empty.
    """
    search_query = request.args.get('q', '').strip().upper()

    if not search_query:
        return jsonify([])

    userId = session.get('user_id')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT user_id, name FROM user WHERE user_id NOT IN (SELECT blocked_user_id FROM blocked_user WHERE user_id = %s) AND name LIKE %s", (userId, '%' + search_query + '%',))
    data = cursor.fetchall()
    cursor.close()

    user_info = [{'user_id': user[0], 'name': user[1]} for user in data]
    return jsonify(user_info)



#---------------feed notification top nav -------------------------
@app.route('/mark_all_as_read', methods=['POST'])
def mark_all_notifications_as_read():
    """
    Marks all notifications as read for the logged-in user.

    This function is a route handler for the '/mark_all_as_read' endpoint. It is triggered when a POST request is made to this endpoint.

    Parameters:
    - None

    Returns:
    - If the user is not logged in, it returns the string "User not logged in".
    - If the user is logged in, it updates the 'is_read' field of all notifications for the user to 1 in the database.
    - It then redirects the user to the 'feed' route.

    Note:
    - This function assumes that the user is already logged in and the 'user_id' is stored in the session.
    - It uses the 'mysql' connection object to execute the SQL query and commit the changes to the database.
    - It is recommended to handle the case where the user is not logged in more gracefully, such as returning a JSON response with an error code and message.
    """
    user_id = session.get('user_id')

    if user_id is None:
        return "User not logged in"  # You might want to handle this case more gracefully

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE notification SET is_read = %s WHERE user_id = %s', (1, user_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('feed'))

@app.route('/notification/<notification_id>/read', methods=['GET', 'POST'])
def mark_notification_as_read(notification_id, redirect = 'feed'):
    """
    Mark a notification as read for a user.

    Args:
    - notification_id (str): The ID of the notification to mark as read.
    - redirect (str, optional): The route to redirect to after marking the notification as read. Defaults to 'feed'.

    Returns:
    - If the user is not logged in, it returns the string "User not logged in".
    - If the user is logged in, it updates the 'is_read' field of the notification with the specified ID for the user to 1 in the database.
    - It then redirects the user to the specified route.

    Note:
    - This function assumes that the user is already logged in and the 'user_id' is stored in the session.
    - It uses the 'mysql' connection object to execute the SQL query and commit the changes to the database.
    - It is recommended to handle the case where the user is not logged in more gracefully, such as returning a JSON response with an error code and message.
    """
    user_id = session['user_id']

    if not user_id:
        return "User not logged in" 

    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE notification SET is_read = %s WHERE id = %s AND user_id = %s', (1, notification_id, user_id))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for(redirect))




#---------------user profile page -------------------------
@app.route("/profile/<int:user_id>", methods=("GET", "POST"))
def profile(user_id):
    """
        This function is responsible for generating a user profile page.
    
        Parameters:
        - current_user (User): The currently logged-in user.
        - user_id (int): The ID of the user whose profile is being viewed.
    
        Returns:
        - render_template: The rendered profile template with the following variables:
            - user (User): The user whose profile is being viewed.
            - is_friend (bool): Indicates whether the current user is a friend of the viewed user.
            - my_profile (bool): Indicates whether the viewed user is the current user.
            - posts (list): A list of posts by the viewed user.
            - friends_count (int): The number of friends the viewed user has.
            - country_name (str): The name of the country associated with the viewed user's profile.
            - profile_rating (int): The profile rating of the viewed user.
            - profile_rating_limit (int): The profile rating limit of the current user.
            - profile_rated_today (int): The number of profile ratings made today by the current user.
            - profile_rating_limit (int): The profile rating limit of the current user.
    """
    post_array = []

    session_user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get all posts of the particular user
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id WHERE user.user_id = %s ORDER BY feed.id DESC', (user_id,))
    user_posts = cursor.fetchall()

    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()

    # get profile rating limit per day
    cursor.execute('SELECT * FROM security')
    profile_rating_limit = cursor.fetchone()['profile_rating']

    # profile rated today
    cursor.execute("SELECT count(*) FROM profile_rating WHERE user_id = %s AND DATE(created_at) = CURDATE() OR DATE(updated_at) = CURDATE()", (session_user_id,))
    profile_rated_today = cursor.fetchone()['count(*)']
    
    profile_rating_remaining = profile_rating_limit - profile_rated_today

    total_likes = 0
    total_trophies = 0

    price_per_like = 0.01
    price_per_trophy = 0.25




    for post in user_posts:
        post_id = post['id']

        # Get the number of comments for the post
        cursor.execute('SELECT COUNT(*) AS comment_count FROM comment WHERE post_id = %s', (post_id,))
        comment_count = cursor.fetchone()
        # print("Comment Count:", comment_count['comment_count'])

        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()
        total_likes += like_count['like_count']

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()
        total_trophies += trophy_count['trophy_count']

        # # Get the number of likes for the post
        # cursor.execute('SELECT COUNT(like_count) AS like_count_post FROM user_amt WHERE post_id = %s', (post_id,))
        # like_count_post = cursor.fetchone()
        # total_likes += like_count_post['like_count_post']

        # # Get the number of trophies for the post
        # cursor.execute('SELECT COUNT(trophy_count) AS trophy_count_post FROM user_amt WHERE post_id = %s', (post_id,))
        # trophy_count_post = cursor.fetchone()
        # total_trophies += trophy_count_post['trophy_count_post']

        # Check if the user has liked the trophy for this post
        cursor.execute('SELECT COUNT(*) AS liked_trophy FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, session_user_id))
        liked_trophy = cursor.fetchone()

        cursor.execute('SELECT comment.*, user.name, user.profile FROM comment LEFT JOIN user ON comment.user_id = user.user_id WHERE post_id = %s', (post_id,))
        comment = cursor.fetchall()

        postObj = {
                'id': post['id'],
                'title': post['title'],
                'chunk': post['chunk'].strip().split('\n\n') if post['chunk'] else [],
                'user_id': post['user_id'],
                'category': post['category'],
                'file': post['file'],
                'name': post['name'],
                'profile': post['profile'],
                'tool': post['tool'],
                'comment_count': comment_count['comment_count'],
                'like_count': like_count['like_count'],
                'trophy_count': trophy_count['trophy_count'],
                'liked_trophy': liked_trophy['liked_trophy'],
                'comment': comment
            }


        post_array.append(postObj)


    


    # Calculate the total cost of likes and trophies in cents
    total_likes_cost = total_likes * price_per_like
    total_trophies_cost = total_trophies * price_per_trophy

    # Calculate the total price in cents
    total_price_cents = total_likes_cost + total_trophies_cost

    # report problem limitation
    cursor.execute('SELECT * FROM security')
    problem_report_limit = cursor.fetchone()['problem_report']

    # reported today count
    cursor.execute('SELECT * FROM report WHERE user_id = %s',(user_id,))
    report = cursor.fetchall()
    total_report_count = len(report)

    today_report_count = 0
    for report in report:
        if report['created_at'].date() == datetime.now().date():
            today_report_count += 1

    problem_report_remaining_limit = problem_report_limit - today_report_count

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

    # Calculate the count of unique users who have rated the profile
    cursor.execute('SELECT COUNT(DISTINCT user_id) AS users_rated_count FROM profile_rating WHERE profile_id = %s', (user_id,))
    users_rated_count = cursor.fetchone()['users_rated_count']


    # Calculate the average rating
    if ratings:
        total_ratings = len(ratings)
        sum_ratings = sum(int(rating['rating_value']) for rating in ratings)
        average_rating = sum_ratings / total_ratings
        average_rating = round(average_rating, 1)  # Round to one decimal place
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

     #show user reward
    cursor.execute('SELECT u.user_id, u.name, COUNT(l.post_id) AS total_likes FROM user u LEFT JOIN feed f ON u.user_id = f.user_id LEFT JOIN likes l ON f.id = l.post_id GROUP BY u.user_id, u.name;')
    user_like = cursor.fetchall()

    #show user trophy
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


    # Calculate the total number of users
    total_users = len(sorted_combined_data)

    # Calculate the desired number of users in the 1st percentile based on the total number of users
    desired_users_in_percentile = total_users // 10

    user_categories = {percentile: [] for percentile in range(1, 11)}

    # Separate users with 0 likes and trophies
    users_with_zero_rank = [user for user in sorted_combined_data if user['total_rank'] == 0]

    # Place users with 0 rank in the 0th percentile
    user_categories[0] = users_with_zero_rank

    # Assign users to percentiles based on their actual rank
    # for idx, user_data in enumerate(sorted_combined_data):
    #     if user_data['total_rank'] != 0:
    #         # Calculate percentile dynamically in reverse (1 being the lowest)
    #         percentile = 10 - (idx * 10) // total_users
    #         user_categories[percentile].append(user_data)

    users_without_zero_rank = [user for user in sorted_combined_data if user['total_rank'] != 0]
    total_users = len(users_without_zero_rank)
    previous_end = 0
    for i in range (0,10):
        # calculate index based on percentile
        start_index = previous_end
        end_index = int(total_users * (i+1) / 10)

        # check if start and end endex are the same
        if start_index == end_index:
            end_index += 1
        # print(start_index,end_index)
        user_categories[10-i] = users_without_zero_rank[start_index:end_index]
        previous_end = end_index

    # Place users with 0 rank in the 0th percentile
    user_categories[0] = users_with_zero_rank

    cursor.execute('SELECT * FROM promoted ORDER BY promoted.id DESC')
    promoted = cursor.fetchall()

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (session_user_id,))
    session_user = cursor.fetchone()

    # total_users = len(sorted_combined_data)
    # for i in range (0,9):
    #     start_index = int(total_users * i / 10)
    #     end_index = int(total_users * (i+1) / 10)
    #     user_categories[10-i] = sorted_combined_data[start_index:end_index]

    return render_template("profile.html", user=user, users=users, total_likes=total_likes, total_likes_cost=total_likes_cost, total_trophies_cost=total_trophies_cost, 
        total_price_cents=total_price_cents, total_trophies=total_trophies, history_count=history_count, like_count=like_count, trophy_count=trophy_count, 
        is_following=is_following, own_profile=own_profile, count=count, average_rating=average_rating, has_given_trophies=has_given_trophies,
        notifications=notifications, notification_count=notification_count, post=post_array, user_categories=user_categories, promoted=promoted, users_rated_count=users_rated_count,
        problem_report_remaining_limit = problem_report_remaining_limit,total_report_count=total_report_count,profile_rating_remaining=profile_rating_remaining, current_user=session_user)


#------------------user edit profile page----------------------
@app.route("/edit/<int:user_id>", methods=["GET", "POST"])
def edit(user_id):
    """
    Edit a user's profile.

    Parameters:
        user_id (int): The ID of the user to edit.

    Returns:
        flask.Response: The rendered template for the edit page, including the user's profile information, notifications, and other relevant data.
    """
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

    # cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    # cursor.close()
    
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (session.get('user_id'),))
    current_user = cursor.fetchone()
    

    return render_template("edit.html", user=user, notifications=notifications,
        notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies, current_user=current_user)




#----------------user edit profile form----------------------
@app.route("/edit_profile/<int:user_id>", methods=["POST"])
def edit_profile(user_id):
    """
    Edit the profile of a user with the given user_id.

    Parameters:
        user_id (int): The ID of the user whose profile is being edited.

    Returns:
        If the request method is POST, the function updates the user's profile information in the database and redirects to the user's profile page.
        If the request method is not POST, the function renders the 'profile.html' template with the user_id as a parameter.

    Side Effects:
        - If a profile image is uploaded, the function saves the image to an AWS S3 bucket and updates the user's profile in the database with the S3 URL.
        - If no profile image is uploaded, the function updates the user's profile in the database with an empty string.
    """
    if request.method == "POST":
        file = request.files['profile']
        name = request.form['name']
        email = request.form['email']
        # password = request.form['password']

        # hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    
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
        cursor.execute('UPDATE user SET name = %s, email = %s, profile = %s WHERE user_id = %s',
                       (name, email, file_path, user_id))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('profile', user_id=user_id))

    return render_template('profile.html', user_id=user_id)



#----------------user delete profile form----------------------
@app.route("/delete_profile/<int:user_id>", methods=["POST"])
def delete_profile(user_id):
    """
    Deletes a user's profile by updating the 'status' field in the 'user' table to 'delete'.
    
    Args:
        user_id (int): The ID of the user whose profile is to be deleted.
    
    Returns:
        If the request method is POST, redirects to the home page with a success flash message.
        If the request method is not POST, renders the 'profile.html' template with the user_id.
    """
    if request.method == "POST":
        status = 'delete'

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE user SET status = %s WHERE user_id = %s',
                       (status, user_id))
        mysql.connection.commit()
        cursor.close()

        # Log out the user by clearing the session
        session.clear()

        flash('Your account has been deleted', 'success')

        return redirect(url_for('home'))  # Redirect to the home page

    return render_template('profile.html', user_id=user_id)


# ---------------------------Delete History-----------------------------------
@app.route('/remove_history', methods=['GET'])
def remove_history():
    """
    Route for removing a history entry.

    This route is responsible for removing a history entry from the database. It expects a GET request with a query parameter 'history_id' specifying the ID of the history entry to be removed. The function retrieves the 'history_id' from the request arguments and executes an SQL query to update the 'deleted_at' field of the corresponding entry in the 'history' table with the current timestamp. The function then commits the changes to the database and returns a JSON response with the key 'status' set to True.

    Parameters:
        None

    Returns:
        dict: A JSON response with the key 'status' set to True if the history entry was successfully removed.

    Raises:
        None
    """
    history_id = request.args.get('history_id')
    current_timestamp = datetime.now()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('UPDATE history SET deleted_at = %s WHERE id = %s', (current_timestamp, history_id,))
    mysql.connection.commit()

    print(history_id)
    return {'status': True}



# ---------------------------Profile Rating Section-----------------------------------
@app.route("/submit_rating/<int:profile_id>", methods=["POST"])
def submit_rating(profile_id):
    """
    Submits a rating for a specific profile by the logged-in user.

    Args:
        profile_id (int): The ID of the profile to submit the rating for.

    Returns:
        redirect: A redirect to the profile page for the specified user.

    Raises:
        None

    Notes:
        - This route requires a POST request.
        - The logged-in user's ID is retrieved from the session.
        - The rating value is obtained from the submitted form data.
        - If the logged-in user has already rated the profile, the existing rating is updated.
        - If the logged-in user has not rated the profile, a new rating is inserted into the database.
        - The average rating for the profile is calculated after the rating is submitted.
        - A flash message is displayed to the user after the rating is submitted.
    """

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
    """
    Renders the 'tokenbuy.html' template for the '/tokenbuy' route. This route is accessible only to logged-in users.
    
    Returns:
        The rendered 'tokenbuy.html' template with the following context variables:
            - product: A list of all products retrieved from the database.
            - notifications: A list of notifications for the logged-in user, ordered by their ID in descending order.
            - user: The user information of the logged-in user.
            - users: A list of all users in the database.
            - notification_count: The count of unread notifications for the logged-in user.
            - total_likes: The total number of likes received by all posts.
            - total_trophies: The total number of trophies received by all posts.
            - current_user: The user information of the currently logged-in user.
    """
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

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (session.get('user_id'),))
    current_user = cursor.fetchone()

    cursor.close()

    return render_template('tokenbuy.html', product=product, notifications=notifications, user=user, users=users, 
        notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies,current_user = current_user)


#----------------------token payment------------------------
@app.route('/token_payment', methods=['POST'])
def token_payment():
    """
    Handles the token payment for a user. This route is accessed via a POST request to '/token_payment'.
    
    :return: A JSON response with the status of the payment. If the user is not logged in, they are redirected to the home page. If the payment is successful, the response contains the status 'Payment successfully'.
    :rtype: flask.Response
    """
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
    """
    Calculates the quantity based on the given price.

    Parameters:
        price (float): The price of the item.

    Returns:
        int: The calculated quantity.
    """
    return price * 96



# ---------------------------Order Page-----------------------------------
@app.route('/order', methods=['GET'])
def order():
    """
    This function handles the '/order' route for the GET method. It checks if the user is logged in and redirects to the login page if not. It then retrieves the user ID from the session.
    
    The function calculates the total number of likes and trophies received by the user for all posts. It iterates over each post and executes SQL queries to retrieve the number of likes and trophies for each post. The total number of likes and trophies is accumulated.
    
    The function retrieves the user information for the current user from the database. It also retrieves the number of unread notifications and the notifications for the user.
    
    The function retrieves the orders for the user from the database.
    
    The function retrieves the withdrawal information for the user from the database.
    
    The function retrieves the current user information from the database.
    
    Finally, the function renders the 'order.html' template with the retrieved data.
    """
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

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM withdraw WHERE user_id = %s", (user_id,))
    withdraw = cursor.fetchall()
    

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (session.get('user_id'),))
    current_user = cursor.fetchone()

    cursor.close()
 
    return render_template('order.html', orders=orders, notifications=notifications, user=user, 
        notification_count=notification_count, total_likes=total_likes, total_trophies=total_trophies, withdraw=withdraw, current_user=current_user)




# ------------------Withdraw money by user by user----------------------
@app.route('/withdraw', methods=['POST'])
def withdraw():
    """
    Handles the POST request to withdraw money from a user's account.

    Parameters:
        None

    Returns:
        A redirect to the 'thank_you' route.

    Raises:
        None
    """
    if request.method == "POST":
        user_id = request.form.get('user_id')
        email = request.form.get('email')
        name = request.form.get('name')
        bank_name = request.form.get('bank_name')
        routing_name = request.form.get('routing_name')
        account_num = request.form.get('account_num')
        amt = request.form.get('amt')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO withdraw (user_id, name, email, bank_name, routing_number, account_number, amount, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())', (user_id, name, email, bank_name, routing_name, account_num, amt))
        mysql.connection.commit()

        cursor.execute("DELETE FROM user_amt WHERE user_id = %s", (user_id,))
        mysql.connection.commit()

    return redirect(url_for('thank_you'))


# ------------------Rport problem by user----------------------
@app.route('/report', methods=['POST'])
def report():
    """
    Route for handling the '/report' endpoint with the POST method.

    This function is responsible for inserting a new report into the database when a user submits a report form.

    Parameters:
        None

    Returns:
        A redirect response to the 'thank_you' endpoint.

    Raises:
        None
    """
    if request.method == "POST":
        user_id = request.form.get('user_id')
        title = request.form.get('title')
        message = request.form.get('message')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute('INSERT INTO report (user_id, title, message, created_at) VALUES (%s, %s, %s, NOW())', (user_id, title, message))
        mysql.connection.commit()

    return redirect(url_for('thank_you'))



#---------------------show follower user in circle tab-------------------
@app.route("/followed_users", methods=["GET"])
def get_followed_users():
    """
    Retrieves the followed users and their information for a given follower user.

    This function is a route handler for the "/followed_users" endpoint and is responsible for retrieving the followed users and their information for a specific follower user. It first checks if the user is logged in by checking the 'loggedin' key in the session. If the user is not logged in, it redirects them to the home page.

    Next, it retrieves the follower user's ID from the session and initializes the total number of likes and total number of trophies to 0. It then executes a query to fetch all the posts from the 'feed' table, along with the corresponding user's name and profile, and orders them by the post's ID in descending order.

    For each post, it calculates the total number of likes and the total number of trophies received by the post. The total number of likes is incremented by the count of likes for each post, and the total number of trophies is incremented by the count of trophies for each post.

    After that, it executes a query to fetch the followed users for the follower user by joining the 'follows' table with the 'user' table and filtering the results based on the follower user's ID.

    Then, it retrieves the names and profiles of the followed users by executing a query for each followed user in the 'user' table. It also retrieves the posts for each user and calculates the total number of trophies received for each post. The total number of trophies is incremented by the count of trophies for each post.
    """
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
        cursor.execute('SELECT user_id,name,profile FROM user WHERE user_id = %s', (user['following_id'],))
        user = cursor.fetchone()

        cursor.execute('SELECT * FROM feed WHERE user_id = %s', (user['user_id'],))
        post = cursor.fetchall()

        totalTrophies = 0
        for p in post:
            postId = p['id']
            cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
            trophy_count = cursor.fetchone()
            totalTrophies += trophy_count['trophy_count']

        level = int(totalTrophies / 10)
        if(level == 0 and totalTrophies > 0):
            level = 1
        if(level > 10):
            level = 10
        user['level'] = level
        user['total_trophies'] = totalTrophies
        followed_users_info.append(user)


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

       #show user reward
    cursor.execute('SELECT u.user_id, u.name, COUNT(l.post_id) AS total_likes FROM user u LEFT JOIN feed f ON u.user_id = f.user_id LEFT JOIN likes l ON f.id = l.post_id GROUP BY u.user_id, u.name;')
    user_like = cursor.fetchall()

    #show user trophy
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


    # Calculate the total number of users
    total_users = len(sorted_combined_data)

    # Calculate the desired number of users in the 1st percentile based on the total number of users
    desired_users_in_percentile = total_users // 10

    user_categories = {percentile: [] for percentile in range(1, 11)}

    # Separate users with 0 likes and trophies
    users_with_zero_rank = [user for user in sorted_combined_data if user['total_rank'] == 0]

    # Place users with 0 rank in the 0th percentile
    user_categories[0] = users_with_zero_rank

    # Assign users to percentiles based on their actual rank
    # for idx, user_data in enumerate(sorted_combined_data):
    #     if user_data['total_rank'] != 0:
    #         # Calculate percentile dynamically in reverse (1 being the lowest)
    #         percentile = 10 - (idx * 10) // total_users
    #         user_categories[percentile].append(user_data)

    users_without_zero_rank = [user for user in sorted_combined_data if user['total_rank'] != 0]
    total_users = len(users_without_zero_rank)
    previous_end = 0
    for i in range (0,10):
        # calculate index based on percentile
        start_index = previous_end
        end_index = int(total_users * (i+1) / 10)

        # check if start and end endex are the same
        if start_index == end_index:
            end_index += 1
        # print(start_index,end_index)
        user_categories[10-i] = users_without_zero_rank[start_index:end_index]
        previous_end = end_index

    # Place users with 0 rank in the 0th percentile
    user_categories[0] = users_with_zero_rank

    cursor.execute('SELECT * FROM user WHERE user_id = %s', (follower_id,))
    current_user = cursor.fetchone()

    # print(user_categories)

    return render_template("followedUser.html", followed_users=followed_users_info, notifications=notifications, user=user, users=users, notification_count=notification_count,
        total_likes=total_likes, total_trophies=total_trophies, user_categories=user_categories,current_user=current_user)



#--------------------------follow user in profile---------------------
@app.route("/follow/<int:user_id>", methods=["POST"])
def follow(user_id):
    """
    Adds a follow relationship between the currently logged-in user and the user with the specified `user_id`.
    If the user is not logged in, they are redirected to the home page.
    
    Parameters:
        user_id (int): The ID of the user to follow.
    
    Returns:
        Redirects the user to the profile page of the followed user.
    """
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
    """
    Unfollows a user with the given user_id.

    Parameters:
        user_id (int): The ID of the user to unfollow.

    Returns:
        redirect: A redirect to the profile page of the unfollowed user.

    Raises:
        None

    Description:
        This function is a route handler for the "/unfollow/<int:user_id>" endpoint. It is called when a user submits a POST request to unfollow another user. 

        First, it checks if the user is logged in. If not, it redirects them to the home page.

        Then, it retrieves the ID of the logged-in user from the session.

        Next, it executes a DELETE query on the "follows" table in the database to remove the follow relationship between the logged-in user and the user to be unfollowed.

        After that, it checks if the unfollow action resulted in the removal of a mutual follow relationship. It does this by executing a SELECT query on the "follows" table to find any follow relationship between the user to be unfollowed and the logged-in user.

        If there is no mutual follow relationship, it retrieves the name of the logged-in user and constructs a notification message. It then saves the notification in the "notification" table in the database.

        Finally, it redirects the user to the profile page of the unfollowed user.

        Note: This function assumes that the necessary database connection and session management have been set up beforehand.
    """
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
    """
    Creates a new post in the feed table of the MySQL database. The post is associated with a user, has a category, a title, and an optional file. The post is also linked to the user's followers, and a notification is created for each follower.

    Parameters:
    - None

    Returns:
    - Redirects to the profile page of the user who posted the content if the request method is POST.
    - Redirects to the feed page if the request method is not POST.

    Raises:
    - None
    """
    if request.method == "POST":
        chunk = request.form.get('chunk')
        user_id = request.form.get('user_id')
        category = request.form.get('category')
        title = request.form.get('paste_prompt')
        file = ''



        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        text = unidecode.unidecode(title).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        cursor.execute('INSERT INTO feed (chunk, user_id, category, title, file, created_at, slug) VALUES (%s, %s, %s, %s, %s, NOW(), %s)', (chunk, user_id, category, title, file, slug))
        mysql.connection.commit()

        flash('You have posted successfully', 'success')

        return redirect(url_for('profile', user_id=user_id))

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


    return redirect(url_for('feed'))



# Function to compress an image to a target file size
def compress_image(image, target_size_kb):
    """
    Compresses an image to a target file size.

    Args:
        image (PIL.Image.Image): The image to be compressed.
        target_size_kb (int): The target file size in kilobytes.

    Returns:
        io.BytesIO: A BytesIO object containing the compressed image data.

    This function compresses an image to a target file size by iteratively reducing the quality of the image. It starts with an initial quality setting of 95 and reduces the quality by 5 for each iteration until the file size is within the target size or the minimum quality is reached. The compressed image is saved as a JPEG format with the updated quality setting.

    Note:
        - The image must be a PIL.Image.Image object.
        - The target_size_kb parameter specifies the target file size in kilobytes.
        - The function returns a BytesIO object containing the compressed image data.

    Example:
        >>> from PIL import Image
        >>> image = Image.open('image.jpg')
        >>> compressed_image = compress_image(image, 100)
        >>> compressed_image.seek(0)
        >>> compressed_image.read()
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01...'
    """
    quality = 95  # Initial quality setting (adjust as needed)
    max_iterations = 10  # Maximum number of iterations
    min_quality = 1  # Minimum allowed quality

    for _ in range(max_iterations):
        # Create a BytesIO object to hold the resized image data
        image_data = io.BytesIO()

        # Save the image to BytesIO in JPEG format with the current quality setting
        image.save(image_data, format='JPEG', quality=quality)
        image_data.seek(0)

        # Check the file size
        file_size_kb = len(image_data.getvalue()) / 1024  # Convert to KB

        if file_size_kb <= target_size_kb:
            break  # Image is within target size, exit loop

        # Reduce quality for the next iteration
        quality -= 5  # You can adjust the step size as needed

        if quality < min_quality:
            break  # Minimum quality reached, exit loop

    return image_data

# Function to compress an image to a png format
def compress_image_png(decoded_image_data, target_size_kb=4096, _new_dimensions=(0, 0)):
	
    """
	Compresses an image to a target size in kilobytes.

	:param decoded_image_data: The binary data of the image to be compressed.
	:type decoded_image_data: bytes
	:param target_size_kb: The target size of the compressed image in kilobytes. Default is 4096.
	:type target_size_kb: int
	:param _new_dimensions: The new dimensions of the image. Default is (0, 0).
	:type _new_dimensions: tuple[int, int]
	:return: A list containing the compressed image data and the new dimensions of the image.
	:rtype: list[bytes, tuple[int, int]]

	This function compresses an image to a target size in kilobytes. It takes in the binary data of the image to be compressed and the target size of the compressed image in kilobytes. It also takes an optional parameter `_new_dimensions` which specifies the new dimensions of the image. The function returns a list containing the compressed image data and the new dimensions of the image.

	The function first creates an in-memory file for the image using the `BytesIO` class. It then opens the image using the `Image.open` method from the Pillow library.

	Next, the function calculates the resize ratio based on the current size and target size.

	The function then enters a while loop to compress the image. It resizes the image using the calculated ratio and saves it as a PNG image in an in-memory file. If the compressed image is below the target size, the function breaks out of the loop.

	If the compressed image is not below the target size, the function adjusts the ratio and tries again. This process continues until the compressed image is below the target size or until the ratio becomes too small.
    """
    
    # Create an in-memory file for the image
    image_file = BytesIO(decoded_image_data)

    # Open the image using Pillow
    image = Image.open(image_file)

    # Calculate the resize ratio based on current size and target
    ratio = (target_size_kb * 1024 / len(decoded_image_data)) ** 0.5

    # Start compressing
    while True:
        # Resize the image
        if(_new_dimensions==(0, 0)):
          new_dimensions = (int(image.width * ratio), int(image.height * ratio))
        else:
           new_dimensions = _new_dimensions
        print(new_dimensions)
        image = image.resize(new_dimensions)

        output_io = BytesIO()
        image.save(output_io, format="PNG")

        # If the compressed image is below the target size, we're done
        if output_io.tell() < target_size_kb * 1024:
            break

        # If not, adjust the ratio and try again
        ratio *= 0.95

        if ratio < 0.1:  # Just a safety check to avoid infinite loops
            raise Exception("Unable to compress the image below the target size.")
        
    print(len(output_io.getvalue()), new_dimensions)

    return [output_io.getvalue(), new_dimensions]

# Define a function to upload the image to AWS S3
# def upload_image_to_s3(file_path, filename):
#     s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

#     # Open the image file
#     with open(file_path, 'rb') as file:
#         # Calculate new dimensions for 50% compression
#         image = Image.open(file)

#         # Ensure the image is in RGB mode (convert from RGBA if needed)
#         if image.mode == 'RGBA':
#             image = image.convert('RGB')

#         # Calculate new dimensions for 50% compression
#         width, height = image.size
#         new_width = int(width * 0.5)
#         new_height = int(height * 0.5)

#         # Resize the image
#         resized_image = image.resize((new_width, new_height))

#         # Compress the image to the target file size
#         compressed_image_data = compress_image(resized_image, target_size_kb=50)

#         # Upload the resized image to S3
#         s3.upload_fileobj(compressed_image_data, BUCKET_NAME, filename, ExtraArgs={'ContentType': 'image/jpeg'})


# ------------------Create post by user----------------------
@app.route('/create_image', methods=['POST'])
def create_image():
    """
    Create an image and upload it to S3.

    This function is a route handler for the '/create_image' endpoint. It is triggered when a POST request is made to this endpoint. The function expects the following form fields in the request:
    - 'user_id': The ID of the user creating the image.
    - 'category': The category of the image.
    - 'paste_prompt': The title of the image.
    - 'file': The image file to be uploaded.
    - 'tool': The tool used to create the image.

    The function first checks if the request method is POST. Then, it retrieves the form data and the uploaded file. If a file is provided, it saves the file to a temporary location and uploads it to S3 using the AWS SDK. The image is resized and compressed to a target size of 50KB. The S3 URL for the uploaded file is obtained, and it is stored in the database along with the other form data.

    After the image is uploaded and stored, the function inserts a notification for each follower of the user posting the content. The notification message includes the username of the post owner.

    Finally, the function redirects the user to their profile page if the upload is successful, or to the feed page if not.

    Parameters:
    None

    Returns:
    - If the upload is successful, it redirects the user to their profile page.
    - If the upload fails, it redirects the user to the feed page.
    """
    if request.method == "POST":
        chunk = ''
        user_id = request.form.get('user_id')
        category = request.form.get('category')
        title = request.form.get('paste_prompt')
        file = request.files['file']
        tool = request.form.get('tool')

        if file:

            filename = secure_filename(file.filename)
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Save the file to a temporary location
            file.save(file_path)

            # Start a separate process to upload the image to S3
            # upload_process = multiprocessing.Process(target=upload_image_to_s3, args=(file_path, filename))
            # upload_process.start()

            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

            # Open the image file
            with open(file_path, 'rb') as file:
                # Calculate new dimensions for 50% compression
                image = Image.open(file)

                # Ensure the image is in RGB mode (convert from RGBA if needed)
                if image.mode == 'RGBA':
                    image = image.convert('RGB')

                # Calculate new dimensions for 50% compression
                width, height = image.size
                new_width = int(width * 0.5)
                new_height = int(height * 0.5)

                # Resize the image
                resized_image = image.resize((new_width, new_height))

                # Compress the image to the target file size
                compressed_image_data = compress_image(resized_image, target_size_kb=50)

                # Upload the resized image to S3
                s3.upload_fileobj(compressed_image_data, BUCKET_NAME, filename, ExtraArgs={'ContentType': 'image/jpeg'})


            # Get the S3 URL for the uploaded file
            s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
            file_path = s3_url


        else:
            file_path = ""

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        text = unidecode.unidecode(title).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        cursor.execute('INSERT INTO feed (chunk, user_id, file, category, title, tool, created_at, slug) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)', (chunk, user_id, file_path, category, title, tool, slug))
        mysql.connection.commit()

        flash('You have posted successfully', 'success')

        return redirect(url_for('profile', user_id=user_id))

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


    return redirect(url_for('feed'))






# ------------------Create post by user----------------------
@app.route('/create_video', methods=['POST'])
def create_video():
    """
    Create a video by processing an uploaded video file and saving it to an S3 bucket.
    The video file is resized to a target resolution and compressed using the libx264 codec.
    The compressed video file is then uploaded to an S3 bucket and the S3 URL is stored in the database.
    The function also creates notifications for the followers of the user posting the content.
    
    Parameters:
    - None
    
    Returns:
    - Redirects to the profile page of the user who posted the content if the video is successfully uploaded and processed.
    - Redirects to the feed page if there is an error during the video processing or upload.
    """
    if request.method == "POST":
        chunk = ''
        user_id = request.form.get('user_id')
        category = request.form.get('category')
        title = request.form.get('paste_prompt')
        video = request.files['video_file']

        if video:
            fileName = secure_filename(video.filename).split('.')[0]
            # Create a temporary file to save the uploaded video
            video_filename = 'original_' + secure_filename(video.filename)
            video.save(video_filename)

            # Load the video using moviepy
            video_clip = VideoFileClip(video_filename)

            # Define a target video resolution (adjust as needed)
            target_resolution = (640, 360)  # Example: 640x360
            
            # renaming compressed file and changing its extension to mp3
            compressed_filename = 'compressed_' + fileName + '.mp4'

            # resize the video to height of 360 maintaing original aspect ratio
            compressed_clip = video_clip.resize(height=480)
            
            # Use the write_videofile method to specify the output bitrate (adjust as needed)
            compressed_clip.write_videofile(compressed_filename, codec='libx264', bitrate='500k')

            s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

            # Upload the compressed video to S3
            s3.upload_file(compressed_filename, BUCKET_NAME, compressed_filename)

            # Get the S3 URL for the uploaded video file
            compressed_video_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{compressed_filename}"
            file_path = compressed_video_s3_url

            # Clean up the temporary files
            os.remove(video_filename)
            os.remove(compressed_filename)
        else:
            file_path = ""

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        text = unidecode.unidecode(title).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug

        cursor.execute('INSERT INTO feed (chunk, user_id, file, category, title, created_at, slug) VALUES (%s, %s, %s, %s, %s, NOW(), %s)', (chunk, user_id, file_path, category, title, slug))
        mysql.connection.commit()

        flash('You have posted successfully', 'success')

        return redirect(url_for('profile', user_id=user_id))

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

    return redirect(url_for('feed'))


#----------------post delete section---------------------------
@app.route("/delete_post/<int:post_id>", methods=("POST",))
def delete_post(post_id):
    """
    Deletes a post with the specified post_id if it belongs to the logged-in user.

    Parameters:
        post_id (int): The ID of the post to be deleted.

    Returns:
        redirect: A redirect to the 'feed' route.

    Raises:
        None
    """
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
    """
    Handles the request to like a post.

    Args:
        post_id (int): The ID of the post to be liked.

    Returns:
        If the user is not logged in, redirects to the home page.
        If the post does not exist, displays an error message.
        If the user does not have enough token balance, displays an error message.
        If the user has not liked the post before, inserts a new like record in the database and updates the like count in the post and user_amt tables.
            Returns a JSON response with the updated like count.
        If the user has already liked the post, updates the like count in the user_amt table for the existing record.
            Returns a JSON response with the updated like count.
    """
    
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM likes WHERE post_id = %s AND user_id = %s', (post_id, user_id))
    like = cursor.fetchone()

    cursor.execute('SELECT user_id FROM feed WHERE id = %s', (post_id,))
    post_user_id = cursor.fetchone()['user_id']

    cursor.execute('SELECT * FROM feed WHERE id = %s', (post_id,))
    post = cursor.fetchone()


    if not post:
        flash("Post does not exist.", 'error')

    else:
        cursor.execute('SELECT token_balance FROM user WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        if user['token_balance'] <= 0:

            flash("Not enough token balance.", 'error')
            return redirect(url_for('feed'))

        elif not like:
            cursor.execute('INSERT INTO likes (user_id, post_id) VALUES (%s, %s)', (user_id, post_id))
            cursor.execute('UPDATE user SET token_balance = token_balance - 1 WHERE user_id = %s', (user_id,))
            mysql.connection.commit()

            # Update the like count in the post
            cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
            like_count = cursor.fetchone()['like_count']

            # Check if there's an existing user_amt record for the same user and post
            cursor.execute('SELECT id FROM user_amt WHERE user_id = %s AND post_id = %s', (post_user_id, post_id))
            existing_record = cursor.fetchone()

            if existing_record:
                # Update the like count in the existing user_amt record
                cursor.execute('UPDATE user_amt SET like_count = %s WHERE id = %s', (like_count, existing_record['id']))
                mysql.connection.commit()
            else:
                # Insert a new user_amt record
                cursor.execute('INSERT INTO user_amt (user_id, post_id, like_count) VALUES (%s, %s, %s)', (post_user_id, post_id, like_count))
                mysql.connection.commit()

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

            # Update the like count in the user_amt table for the existing record
            cursor.execute('UPDATE user_amt SET like_count = %s WHERE user_id = %s AND post_id = %s', (like_count, post_user_id, post_id))
            mysql.connection.commit()

            return jsonify(like_count=like_count)
        




#-----------------trophy share section----------------------
@app.route("/trophy_post/<int:post_id>", methods=["GET"])
def trophy_post(post_id):
    """
    This function handles the GET request for sharing a trophy on a post. It takes in a post_id as a parameter and checks if the user is logged in. If the user is not logged in, it redirects to the home page. 

    It then retrieves the user_id from the session and executes a query to check if the user has already shared a trophy on the post. If the user has not shared a trophy, it inserts a new record into the trophy table, updates the user's token balance, and updates the trophy count in the post and the user_amt table. It also inserts a notification for the post owner. Finally, it returns the updated trophy count and the liked trophy count as a JSON response.

    If the user has already shared a trophy on the post, it retrieves the current trophy count and the liked trophy count and updates the trophy count in the user_amt table. It then returns the current trophy count and the liked trophy count as a JSON response.

    Parameters:
    - post_id (int): The ID of the post to share a trophy on.

    Returns:
    - JSON response: The updated trophy count and the liked trophy count.
    """
    if 'loggedin' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute('SELECT * FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, user_id))
    trophy = cursor.fetchone()

    cursor.execute('SELECT user_id FROM feed WHERE id = %s', (post_id,))
    post_user_id = cursor.fetchone()['user_id']

    cursor.execute('SELECT * FROM feed WHERE id = %s', (post_id,))
    post = cursor.fetchone()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id ORDER BY feed.id DESC')
    post = cursor.fetchall()


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

            cursor.execute('SELECT COUNT(*) AS liked_trophy FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, user_id))
            liked_trophy = cursor.fetchone()['liked_trophy']

            # Check if there's an existing user_amt record for the same user and post
            cursor.execute('SELECT id FROM user_amt WHERE user_id = %s AND post_id = %s', (post_user_id, post_id))
            existing_record = cursor.fetchone()

            if existing_record:
                # Update the like count in the existing user_amt record
                cursor.execute('UPDATE user_amt SET trophy_count = %s WHERE id = %s', (trophy_count, existing_record['id']))
                mysql.connection.commit()
            else:
                # Insert a new user_amt record
                cursor.execute('INSERT INTO user_amt (user_id, post_id, trophy_count) VALUES (%s, %s, %s)', (post_user_id, post_id, trophy_count))
                mysql.connection.commit()


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
            return jsonify(trophy_count=trophy_count, liked_trophy=liked_trophy)
        else:
            # If the user has already liked the post, return the current like count
            cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
            trophy_count = cursor.fetchone()['trophy_count']

            cursor.execute('SELECT COUNT(*) AS liked_trophy FROM trophy WHERE post_id = %s AND user_id = %s', (post_id, user_id))
            liked_trophy = cursor.fetchone()['liked_trophy']

             # Update the like count in the user_amt table for the existing record
            cursor.execute('UPDATE user_amt SET trophy_count = %s WHERE user_id = %s AND post_id = %s', (trophy_count, post_user_id, post_id))
            mysql.connection.commit()

            return jsonify(trophy_count=trophy_count, liked_trophy=liked_trophy)  




# -------------------------Create comment-----------------------------
@app.route("/create_comment/<int:post_id>", methods=("POST",))
def create_comment(post_id):
    """
    Creates a new comment for a post.

    Parameters:
        post_id (int): The ID of the post to which the comment is being added.

    Returns:
        dict: A dictionary containing the name of the user who created the comment, the text of the comment, and any other relevant data.

    Raises:
        None

    Side Effects:
        - Inserts a new comment into the database.
        - Commits the changes to the database.

    Dependencies:
        - The user must be logged in.
        - The 'mysql' and 'session' objects must be available.

    Notes:
        - The 'text' parameter is obtained from the 'text' field of the request form.
        - The 'user_id' and 'user_name' are obtained from the 'session' object.
        - The comment is added to the 'comment' table in the database.
        - The 'new_comment' dictionary is returned as a JSON response.

    """
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





# @socketio.on('feed_generate')
# def feed_generate(form):
#     model_engine = 'text-davinci-003'
#     animal = form['animal'];
#     radio = form['radio'];
#     user_id = form['user_id']

#     prompt = animal + ' ' + radio

#     response = openai.Completion.create(
#         engine=model_engine,
#         prompt=generate_feed(prompt),
#         max_tokens=2049,
#         n=1,
#         stop=None,
#         temperature=0.05
#     )
#     full_answer_text = response.choices[0].text.strip()
    
#     # Split answer into words or tokens for streaming
#     tokens = full_answer_text.split()
    
#     streamed_answer = ""

#     for token in tokens:
#         streamed_answer += token + " "
#         socketio.emit('answer_chunk', {'answer_chunk': streamed_answer})
#         time.sleep(0.1)


#     chunks = split_text_into_chunks(full_answer_text, MAX_CHARS_PER_CHUNK)
#     combined_chunks = '\n\n'.join(chunks)

#     # Add code to insert response into the database
#     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#     cursor.execute('INSERT INTO history (title, content, user_id, category, created_at) VALUES (%s, %s, %s, %s, NOW())', (animal, combined_chunks, user_id, radio))
#     mysql.connection.commit()



# @socketio.on('free_generate')
# def free_generate(form):
#     model_engine = 'text-davinci-003'
#     animal = form['animal'];
#     radio = form['radio'];

#     prompt = animal + ' ' + radio

#     response = openai.Completion.create(
#         engine=model_engine,
#         prompt=generate_feed(prompt),
#         max_tokens=2049,
#         n=1,
#         stop=None,
#         temperature=0.05
#     )
#     full_answer_text = response.choices[0].text.strip()
    
#     # Split answer into words or tokens for streaming
#     tokens = full_answer_text.split()
    
#     streamed_answer = ""

#     for token in tokens:
#         streamed_answer += token + " "
#         socketio.emit('answer_chunk', {'answer_chunk': streamed_answer})
#         time.sleep(0.1)


#     chunks = split_text_into_chunks(full_answer_text, MAX_CHARS_PER_CHUNK)
#     combined_chunks = '\n\n'.join(chunks)


#------------render data from openai and save to history----------
# @app.route('/feed_generate', methods=['POST'])
# def feed_generate():  
#     post = request.form["post"]
#     user_id = request.form["user_id"]
#     selection = request.form["selection"]
#     animal = selection + " " + post

#     chunks = request.form.getlist("chunk")



#     if request.method == "POST":


#         animal = animal

#         chunks = []
        
#         response = openai.Completion.create(
#             engine=model_engine,
#             prompt=generate_feed(animal),
#             max_tokens=2049,
#             n=1,
#             stop=None,
#             temperature=0.05,
#         )

#         text = response.choices[0].text
#         chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)

#         combined_chunks = '\n\n'.join(chunks)

#         #add to database
#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('INSERT INTO history (title, content, user_id, category) VALUES (%s, %s, %s, %s)', (animal, combined_chunks, user_id, selection))
#         mysql.connection.commit()


#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('SELECT * FROM history')
#         history = cursor.fetchall()

#         return jsonify({
#             'chunks': chunks,
#             'history': history
#         })

   
#     chunks = request.args.get("chunks")
#     if chunks is not None:
#         chunks = chunks.split(",")

#     return jsonify({
#             'chunks': chunks,

#         })


# Create a function to handle OpenAI processing
def openai_processing(animal, model_engine, result_queue):
    """
    Processes the given animal using the OpenAI API to generate a response.
    
    Args:
        animal (str): The animal to generate a response for.
        model_engine (str): The OpenAI model engine to use for generating the response.
        result_queue (Queue): The queue to put the result chunks in.
    
    Returns:
        None
    
    Raises:
        None
    """
    response = openaiClient.chat.completions.create(
        model=model_engine,
        messages=[
            {"role":"system", "content": generate_feed(animal)},
        ],
        max_tokens=2049,
        n=1,
        stop=None,
        temperature=0.05,
    )
    text = response.choices[0].message.content
    chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)
    
    # Put the result in the queue
    result_queue.put(chunks)



@app.route('/feed_generate', methods=['POST'])
def feed_generate():
    """
    Route for generating feed content based on user input.
    
    This function is responsible for handling the '/feed_generate' route with the 'POST' method. It retrieves the user's input from the request form and performs the following steps:
    
    1. Constructs the 'animal' string by concatenating the user's selection and post.
    2. Creates a queue for interprocess communication.
    3. Starts a separate process for OpenAI processing, passing the 'animal' string, 'model_engine', and the result queue as arguments.
    4. Waits for the OpenAI process to finish.
    5. Retrieves the result from the result queue.
    6. Joins the retrieved chunks into a single string.
    7. Inserts the 'animal' string, combined chunks, user ID, and selection into the 'history' table in the database.
    8. Retrieves the user's history from the 'history' table.
    9. Retrieves the generate limit from the 'security' table.
    10. Counts the number of generates for the current date.
    11. Calculates the remaining generate limit by subtracting the today's generate count from the generate limit.
    12. Returns a JSON response containing the generated chunks, the most recent history entry, and the remaining generate limit.
    
    Parameters:
        None
    
    Returns:
        A JSON response containing the generated chunks, the most recent history entry, and the remaining generate limit.
        If there is an error, a JSON response with the error message is returned.
    
    Raises:
        None
    """
    post = request.form["post"]
    user_id = request.form["user_id"]
    selection = request.form["selection"]
    animal = selection + " " + post

    if request.method == "POST":
        # Create a queue for interprocess communication
        result_queue = multiprocessing.Queue()
        
        # Start OpenAI processing in a separate process
        openai_process = multiprocessing.Process(target=openai_processing, args=(animal, model_engine, result_queue))
        openai_process.start()
        
        # Wait for the OpenAI process to finish
        openai_process.join()

        # Retrieve the result from the queue
        chunks = result_queue.get()

        try:
            combined_chunks = "\n\n".join(chunks)

            # Add to database
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('INSERT INTO history (title, content, user_id, category) VALUES (%s, %s, %s, %s)', (animal, combined_chunks, user_id, selection))
            mysql.connection.commit()

            cursor.execute('SELECT * FROM history WHERE user_id = %s AND deleted_at IS NULL', (user_id,))
            history = cursor.fetchall()
            recent = history[-1]

            cursor.execute('SELECT * FROM security')
            generate_limit = cursor.fetchone()['generate']
            today_generate_count = 0

            for generate in history:
                if generate['created_at'].date() == datetime.now().date():
                    today_generate_count += 1
                    

            remaining_limit = generate_limit - today_generate_count


            return jsonify({
                'chunks': chunks,
                'recent': recent,
                'remaining_limit': remaining_limit

            })

        except Exception as e:
            # Handle any database errors here
            return jsonify({'error': str(e)})



def generate_feed(animal):
    prompt = f"Write about {animal}"
    return prompt



#------------- Store the data produce by openai to db----------------------
@app.route("/store_data", methods=['POST'])
def store_data():
    """
    Store the data produced by OpenAI in the database.

    This function is responsible for handling the POST request to the '/store_data' route. It stores the data generated by OpenAI in the database. The data includes the chunks, title, category, user ID, and post. The function first checks if the user is logged in. If not, it redirects them to the login page. It then retrieves the data from the request form and formats it accordingly. The chunks are converted into a string if they are provided as an array. The title is determined based on the category and post values, or an empty string if neither is provided. The category is parsed from the request form or the radio input value. The function then inserts the data into the 'feed' table in the database. It also retrieves the followers of the current user and inserts notifications for each follower. Finally, it redirects the user to their profile page.

    Parameters:
    - None

    Returns:
    - A redirect response to the user's profile page.

    Raises:
    - None
    """
    if not session.get('loggedin'):
        # User is not logged in, redirect to the login page
        return redirect(url_for('home'))

    chunks = request.form.get('chunks')
    title_data = request.form.get('title')
    cat_data = request.form.get('cat')
    user_id = request.form.get('user_id')
    category = request.form.get('radioInput')
    post = request.form["post"]
    
    # format chunks into a string
    chunks = json.loads(chunks)

    # check if chunks is array then convert into string
    if isinstance(chunks, list):
        chunks = "\n\n".join(chunks)

    if title_data:
        title = request.form.get('title')
    elif category:
        title = category + " " + post
    else:
        title = ""


    if cat_data:
        category = json.loads(cat_data)
    else:
        category = request.form.get('radioInput')




    if request.method == "POST" and 'list-add' in request.form:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        text = unidecode.unidecode(title).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        cursor.execute('INSERT INTO feed (title, chunk, user_id, category, created_at, slug) VALUES (%s, %s, %s, %s, NOW(), %s)', (title, chunks, user_id, category, slug))
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

        return redirect(url_for('profile', user_id=user_id))



#-------------------show generate page----------------
@app.route("/content", methods=("GET", "POST"))
def content():
    """
    This function is a route handler for the "/content" endpoint. It handles both GET and POST requests.

    Parameters:
    None

    Returns:
    The rendered template "content.html" with the prompts data passed as a parameter.

    Raises:
    None
    """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM prompt ORDER BY prompt.id')
    prompts = cursor.fetchall()

    return render_template("content.html", prompts=prompts)

#------------render data from openai and save to history----------
@app.route('/content_process', methods=['POST'])
def content_process():  
    """
    This function is a route handler for the '/content_process' endpoint. It handles POST requests and is responsible for processing the form data submitted from the client.

    Parameters:
    - None

    Returns:
    - If the request method is POST:
    - A JSON response containing the processed chunks, form_disabled status, and history data.
    - If the request method is not POST:
    - A JSON response containing the chunks and form_disabled status.

    Raises:
    - None
    """
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
        
        response = openaiClient.chat.completions.create(
            model=model_engine,
            messages=[
                {"role":"system", "content": generate_feed(animal)},
            ],
            max_tokens=2049,
            n=1,
            stop=None,
            temperature=0.05,
        )
        

        # Split the response text into chunks
        text = response.choices[0].message.content
        chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)

        combined_chunks = '\n\n'.join(chunks)

        #add to database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO history (title, content, user_id, category) VALUES (%s, %s, %s, %s)', (animal, combined_chunks, None, selection))
        mysql.connection.commit()
        cursor.close()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM history WHERE deleted_at IS NUL')
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


#------------render data from openai and save to history----------
# @app.route('/feed_process', methods=['POST'])
# def feed_generate():  
#     post = request.form["post"]
#     user_id = request.form["user_id"]
#     selection = request.form["selection"]
#     animal = selection + " " + post

#     chunks = request.form.getlist("chunk")



#     if request.method == "POST":


#         animal = animal

#         chunks = []
        
#         response = openai.Completion.create(
#             engine=model_engine,
#             prompt=generate_feed(animal),
#             max_tokens=680,
#             n=1,
#             stop=None,
#             temperature=0.05,
#         )

#         text = response.choices[0].text
#         chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)

#         combined_chunks = '\n\n'.join(chunks)

#         #add to database
#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('INSERT INTO history (title, content, user_id, category) VALUES (%s, %s, %s, %s)', (animal, combined_chunks, None, selection))
#         mysql.connection.commit()


#         cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#         cursor.execute('SELECT * FROM history')
#         history = cursor.fetchall()

#         return jsonify({
#             'chunks': chunks,
#             'history': history
#         })

   
#     chunks = request.args.get("chunks")
#     if chunks is not None:
#         chunks = chunks.split(",")

#     return jsonify({
#             'chunks': chunks,

#         })


def generate_content(animal):
    """
    Generates a prompt for writing about a specific animal.

    Args:
        animal (str): The name of the animal.

    Returns:
        str: The generated prompt for writing about the animal.
    """
    prompt = f"Write about {animal}"
    return prompt



# -------------------------Personalize education--------------------------------
@app.route("/studentDashboard", methods=("GET", "POST"))
def studentDashboard():
    """
    Renders the student dashboard HTML template.

    This route handles both GET and POST requests to the "/studentDashboard" endpoint.
    It does not take any parameters.

    Returns:
        A rendered HTML template for the student dashboard.
    """
    return render_template("studentDashboard.html")

# Personalize education
@app.route('/process', methods=['POST'])
def process():  
    """
    This function handles the '/process' route for both POST requests. It retrieves the values of 'grade' and 'subject' from the request form, concatenates them to form the 'animal' variable. It then performs further processing instead of returning a value.

    The function checks if the form has been submitted before by retrieving the value of 'my_form_submitted_key' from the session. If the form has been submitted more than 100 times, it disables the form by setting the value of 'my_form_disabled_key' in the session to True.

    If the request method is POST and the form contains the key 'form-add', the function increments the value of 'my_form_submitted_key' in the session and performs OpenAI chat completions using the 'generate_peducation' function. The response text is split into chunks and redirected to the 'content' route with the chunks and form_disabled parameters.

    If the request method is not POST or the form does not contain the key 'form-add', the function retrieves the value of 'chunks' from the request arguments and redirects to the 'content' route with the chunks and form_disabled parameters.

    Parameters:
    - None

    Returns:
    - A redirect response to the 'content' route with the chunks and form_disabled parameters.
    """
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
        
        response = openaiClient.chat.completions.create(
            model=model_engine,
            messages=[{"role":"system", "content": generate_peducation(animal)}],
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
    """
    Generates a formatted education string based on the provided animal.

    Parameters:
        animal (str): The name of the animal.

    Returns:
        str: The formatted education string.
    """
    return """ {}
""".format(
        animal.capitalize()
    )





# ---------------------------Education query-----------------------------------
@app.route("/education", methods=("GET", "POST"))
def education():
    """
    Route for handling the "/education" endpoint. Supports both GET and POST requests.

    This function handles the logic for generating education content based on user input. It first checks if the form has been submitted before. If the form is submitted and the 'form-add' key is present in the request form, it increments the number of submissions and checks if the form should be disabled after 10 submissions. It then generates education content using the OpenAI API and splits the response text into chunks. Finally, it renders the "index.html" template with the generated chunks and the form disabled status.

    If the form is submitted and the 'correct-grammer' key is present in the request form, it performs the same steps as above but generates content for correcting grammar.

    If the request method is GET, it retrieves the chunks from the request arguments and renders the "index.html" template with the retrieved chunks and the form disabled status.

    Parameters:
    - None

    Returns:
    - A rendered template "index.html" with the generated chunks and the form disabled status.
    """
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
        
        response = openaiClient.chat.completions.create(
            model=model_engine,
            messages=[{"role":"system", "content": prompt_education(animal)}],
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
        
        response = openaiClient.chat.completions.create(
            model= model_engine,
            messages=[{"role":"system", "content": correct_grammer(animal)}],
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
    """
    Generates a prompt for searching information about a specific animal.

    Args:
        animal (str): The name of the animal to search information about.

    Returns:
        str: The generated prompt for searching information about the animal.
    """
    prompt = f"Search information about {animal}"
    return prompt


def correct_grammer(animal):
    """
    Generates a prompt for correcting grammar for a given animal.

    Parameters:
        animal (str): The name of the animal.

    Returns:
        str: The prompt for correcting grammar, with the animal name capitalized.
    """
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
    """
    Splits a given text into chunks of a maximum number of characters per chunk.
    
    Parameters:
        text (str): The text to be split into chunks.
        max_chars_per_chunk (int): The maximum number of characters per chunk.
        
    Returns:
        list: A list of strings, where each string represents a chunk of the text.
    """
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
    """
    Splits the given text into a list of chunks, where each chunk contains a maximum number of characters.
    
    Parameters:
        text (str): The text to be split into chunks.
        max_chars_per_chunk (int): The maximum number of characters allowed in each chunk.
    
    Returns:
        list: A list of strings, where each string represents a chunk of the text.
    """
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
    """
    Calculates the delay in seconds based on the given text.

    Parameters:
        text (str): The input text to calculate the delay for.

    Returns:
        float: The calculated delay in seconds.

    This function calculates the delay in seconds based on the number of words in the given text. It divides the total number of words by the number of words per second (calculated as `WORDS_PER_MINUTE` divided by 60) to get the delay in seconds.

    Example:
        >>> calculate_delay("Hello, world!")
        0.25
    """
    words_per_second = WORDS_PER_MINUTE / 60
    num_words = len(text.split())
    delay = num_words / words_per_second
    return delay

def sleep(value):
    """
    Sleeps for a specified amount of time based on the calculated delay.

    Parameters:
        value (str): The input value used to calculate the delay.

    Returns:
        Markup: An empty Markup object.

    This function calculates the delay using the `calculate_delay` function and then sleeps for the calculated delay using the `time.sleep` function. After sleeping, it returns an empty Markup object.

    Example:
        >>> sleep("Hello, world!")
        Markup('')
    """
    delay = calculate_delay(value)
    time.sleep(delay)
    return Markup('')




#-----------------------Google Login-------------------------
@app.route('/google/login')
def google_login():
    """
    A route decorator that handles the '/google/login' endpoint.
    
    This function is responsible for handling the Google login process. It uses the `google` object to authorize the user and redirect them to the Google callback URL. The callback URL is generated using the `url_for` function with the 'google_callback' endpoint and the `_external=True` parameter.
    
    Returns:
        The authorization response from the Google API.
        
    """
    return google.authorize(callback=url_for('google_callback', _external=True))


#---------------------Google callback function------------------------
@app.route('/google/callback')
@google.authorized_handler
def google_callback(resp):
    """
    A route decorator that handles the '/google/callback' endpoint.
    
    This function is responsible for handling the callback from the Google OAuth2 login process. It is decorated with `@google.authorized_handler`, which means it will be called when the authorization process is successful.
    
    Parameters:
        resp (dict): The response from the Google API containing the access token.
        
    Returns:
        If the authorization is denied or the access token is not present in the response, it returns a string with the reason and error message.
        Otherwise, it performs the following steps:
        - Retrieves the user data from the Google API using the access token.
        - Checks if the user already exists in the 'user' table of the MySQL database.
        - If the user doesn't exist, it creates a new entry in the 'user' table with the user's full name, email, empty password, initial token balance of 100, and profile image URL.
        - If the user already exists, it updates the user's name in the 'user' table.
        - Sets the session data for the logged-in user, including user ID, name, email, and logged-in status.
        - Redirects the user to the feed or homepage after successful login.
    """
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
    """
    Route for user login.

    This route handles both GET and POST requests to the "/login" endpoint. It checks if the request method is POST and if the 'email' and 'password' fields are present in the request form. If so, it retrieves the user from the database based on the provided email. If the user exists and the password matches the hashed password stored in the database, it checks the user's status. If the status is 'delete', it flashes an error message indicating that the account has been deleted. Otherwise, it sets the 'loggedin', 'user_id', 'name', and 'email' fields in the session and redirects the user to the 'feed' route. If the user does not exist or the password is incorrect, it flashes an error message indicating invalid email or password.

    Returns:
        - If the request method is GET, it redirects the user to the 'home' route.
        - If the request method is POST and the login is successful, it redirects the user to the 'feed' route.
        - If the request method is POST and the login fails, it redirects the user to the 'home' route.
    """
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            if user['status'] == 'delete':
                flash('Your account has been deleted', 'error')
            else:
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
    """
    Registers a new user by inserting their information into the database.

    This function is a route handler for the '/register' URL. It handles both GET and POST requests.

    Parameters:
        None

    Returns:
        redirect: A redirect to the 'home' page if the request method is not POST or if the required form fields are not present.
        redirect: A redirect to the 'feed' page if the user is successfully registered.

    Raises:
        None

    Description:
        This function first checks if the request method is POST and if the required form fields ('name', 'password', 'email') are present. If not, it redirects the user to the 'home' page.

        If the form fields are present, the function proceeds to validate the email address and check if the account already exists in the database. If the account exists, it displays an error message. If the email domain is not one of the valid domains, it displays an error message. If the email address is not in a valid format, it displays an error message. If any of the required form fields are empty, it displays an error message.

        If all the validations pass, the function hashes the password using bcrypt and inserts the user's information into the 'user' table in the database. It then commits the changes and displays a success message. Finally, it redirects the user to the 'feed' page.

    """
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form and 'email' in request.form:
        userName = request.form['name']
        password = request.form['password']
        email = request.form['email']
        token_balance = request.form['token_balance']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')  # Hash the password
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        account = cursor.fetchone()

        # Additional email validation for Gmail, Outlook, and Yahoo Mail
        valid_email_domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com', 'live.com', 'usa.com', 'post.com', 'protonmail.com', 'icloud.com', 'proton.me']
        email_domain = email.split('@')[-1].lower()
        
        if account:
            flash('Account already exists!', 'error')
        elif email_domain not in valid_email_domains:
            flash('Invalid email domain! Please use Gmail, Outlook, or Yahoo Mail.', 'error')
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash('Invalid email address!', 'error')
        elif not userName or not password or not email:
            flash('Please fill out the form!', 'error')
        else:
            cursor.execute('INSERT INTO user (name, email, password, token_balance) VALUES (%s, %s, %s, %s)', (userName, email, hashed_password, token_balance,))
            mysql.connection.commit()
            flash('You have registered successfully. Please login to continue..', 'success')
            return redirect(url_for('feed'))

    return redirect(url_for('home'))




#---------------Forget password page-----------------
@app.route('/forgot', methods =['GET', 'POST'])
def forgot():
    """
    Handles the forgot password functionality. This route is accessed via a GET or POST request to '/forgot'.
    
    :return: If the user is already logged in, they are redirected to the home page. If the request method is POST, the email is extracted from the form data and a token is generated using uuid.uuid4(). The user's information is retrieved from the database based on the email. If a matching user is found, a password reset link is sent to their email and the user's token is updated in the database. If no matching user is found, an error message is displayed. If the request method is GET, the forgot.html template is rendered.
    :rtype: flask.Response
    """
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
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    """
    Handles the reset password functionality for a user. This route is accessed via a GET or POST request to '/reset/<token>'.
    
    :param token: A unique token generated for the user's password reset request.
    :type token: str
    
    :return: If the user is logged in, they are redirected to the home page. If the request method is POST, the function checks if the provided passwords match. If they don't match, the function renders the 'reset.html' template with an error message. If the passwords match, the function hashes the new password and updates the user's password and token in the database. The function then redirects the user to the home page with a success message. If the user's token is invalid, the function renders the 'reset.html' template with an error message. If the request method is not POST, the function renders the 'reset.html' template.
    :rtype: flask.Response
    """
    if 'login' in session:
        return redirect('/')

    if request.method == 'POST':
        password = request.form['password']
        c_password = request.form['c_password']
        token1 = str(uuid.uuid4())

        if password != c_password:
            message = 'Your password does not match'
            return render_template('reset.html', message=message)
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')  # Hash the new password
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE token = %s', (token,))
        user = cursor.fetchone()

        if user:
            cursor.execute('UPDATE user SET token = %s, password = %s WHERE token = %s', (token1, hashed_password, token,))
            mysql.connection.commit()
            cursor.close()
            message = 'Your password has been successfully updated.'
            return redirect(url_for('home', message=message))
            # return render_template('home.html', message=message)
        else:
            message = 'Your token is invalid.'
            return render_template('reset.html', message=message)

    return render_template('reset.html')



#--------------------------User logout--------------------------
@app.route('/logout')
def logout():
    """
    Logs out the user by removing the 'loggedin', 'user_id', and 'email' keys from the session.
    
    :return: A redirect response to the 'home' route.
    :rtype: flask.Response
    """
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('email', None)
    return redirect(url_for('home'))



#-------------------------Custom Error handling if 404--------------------------
@app.errorhandler(404)
def page_not_found(e):
    """
    Handles the error when a 404 error occurs.

    This function is a custom error handler for the Flask application. It is decorated with `@app.errorhandler(404)` to handle 404 errors.

    Parameters:
    - e: The exception object representing the 404 error.

    Returns:
    - A tuple containing the rendered template for the 404 error page and the HTTP status code 404.

    This function renders the "404.html" template to display the error page when a 404 error occurs. It returns the rendered template and the HTTP status code 404.

    Note:
    - This function is used to handle the 404 error and provide a custom error page to the user.
    """
    return render_template("404.html"), 404

#--------------------------Custom Error handling if 500--------------------------
@app.errorhandler(500)
def page_not_found(e):
    """
    Handles the error when a 500 error occurs.

    This function is a custom error handler for the Flask application. It is decorated with `@app.errorhandler(500)` to handle 500 errors.

    Parameters:
    - e: The exception object representing the 500 error.

    Returns:
    - A tuple containing the rendered template for the 500 error page and the HTTP status code 500.

    This function renders the "500.html" template to display the error page when a 500 error occurs. It returns the rendered template and the HTTP status code 500.

    Note:
    - This function is used to handle the 500 error and provide a custom error page to the user.
    """
    return render_template("500.html"), 500

#--------------terms and condition page-------------------

@app.route('/terms', methods=['GET', 'POST'])
def terms():
    """
    Route for handling the '/terms' endpoint.
    
    This function handles GET and POST requests to the '/terms' endpoint. It renders the 'terms.html' template and returns it as a response.
    
    Returns:
        A rendered template of 'terms.html'.
    """
    return render_template('terms.html')


@app.route('/privacy', methods=['GET', 'POST'])
def privacy():
    """
    Route for handling the '/privacy' endpoint.
    
    This function handles GET and POST requests to the '/privacy' endpoint. It renders the 'privacy.html' template and returns it as a response.
    
    Returns:
        A rendered template of 'privacy.html'.
    """
    return render_template('privacy.html')


#------------------thank you page-----------------
@app.route('/thank_you', methods=['GET', 'POST'])
def thank_you():
    """
    Route for handling the '/thank_you' endpoint.
    
    This function handles GET and POST requests to the '/thank_you' endpoint. It renders the 'thank.html' template and returns it as a response.
    
    Returns:
        A rendered template of 'thank.html'.
    """
    return render_template('thank.html')


#------------------thank you page-----------------
@app.route('/guide', methods=['GET', 'POST'])
def guide():
    """
    Route for handling the '/guide' endpoint.
    
    This function handles GET and POST requests to the '/guide' endpoint. It retrieves the user's information from the database, including the number of notifications and posts they have. It also calculates the total number of likes and trophies for the user's posts. Finally, it renders the 'guide.html' template and returns it as a response.
    
    Returns:
        A rendered template of 'guide.html' with the user's information, notifications, number of notifications, total likes, total trophies, and current user.
    """
    user_id = session['user_id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    # Get the number of trophies for the post
    cursor.execute('SELECT COUNT(*) AS notification_count FROM notification WHERE user_id = %s  AND is_read = 0', (user_id,))
    notification_count = cursor.fetchone()['notification_count']


    # Retrieve the notifications for the user
    cursor.execute('SELECT notification.*, user.name, user.profile FROM notification JOIN user ON notification.user_id = user.user_id WHERE notification.user_id = %s ORDER BY notification.id DESC', (user_id,))
    notifications = cursor.fetchall()

    # Get all posts of the particular user
    cursor.execute('SELECT feed.*, user.name, user.profile FROM feed JOIN user ON feed.user_id = user.user_id WHERE user.user_id = %s ORDER BY feed.id DESC', (user_id,))
    user_posts = cursor.fetchall()

    total_likes = 0
    total_trophies = 0
    for p in user_posts:
        post_id = p['id']
        
        # Get the number of likes for the post
        cursor.execute('SELECT COUNT(*) AS like_count FROM likes WHERE post_id = %s', (post_id,))
        like_count = cursor.fetchone()
        total_likes += like_count['like_count']

        # Get the number of trophies for the post
        cursor.execute('SELECT COUNT(*) AS trophy_count FROM trophy WHERE post_id = %s', (post_id,))
        trophy_count = cursor.fetchone()
        total_trophies += trophy_count['trophy_count']


    cursor.execute('SELECT * FROM user WHERE user_id = %s', (session.get('user_id'),))
    current_user = cursor.fetchone()

    return render_template('guide.html', user=user,notifications=notifications, notification_count=notification_count,total_likes=total_likes,total_trophies=total_trophies, current_user=current_user)




@app.route("/dalle", methods=("GET", "POST"))
def dalle():
    """
    Renders the DALL-E webpage with a list of images fetched from the 'images' table in the MySQL database.

    :return: A rendered HTML template 'dalle.html' with a list of images.
    :rtype: flask.Response
    """
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT url FROM images")
    images = cursor.fetchall()

    return render_template('dalle.html', images=images)



# generate image using dall-e
@app.route("/generate_img", methods=['POST'])
def generate_img():
    """
    Generates an image using the DALL-E model based on the provided prompt.
    
    This function is a route handler for the '/generate_img' endpoint. It expects a POST request with a 'prompt' parameter in the request form. 
    
    Parameters:
    - None
    
    Returns:
    - A rendered HTML template 'dalle.html' with the generated image URL.
    
    Raises:
    - None
    """
    prompt = request.form["prompt"]

    if request.method == 'POST':

        response = openaiClient.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            quality="standard",
            size="256x256",
        )

    img = response['data'][0]['url']

    return render_template('dalle.html', img=img)


@app.route("/save_image", methods=['POST'])
def save_image():
    """
    Save an image from a URL to an S3 bucket and insert the image URL into the database.
    
    This function is an endpoint for the '/save_image' route, which is accessed via a POST request. It receives the following parameters from the request form:
    - 'url': The URL of the image to be saved.
    - 'user_id': The ID of the user who is posting the image.
    - 'category': The category of the image.
    - 'paste_prompt': The prompt associated with the image.
    
    If the 'url' parameter is present, the function downloads the image from the URL, compresses it to a target size, saves it to a temporary file, and uploads it to an S3 bucket. The S3 URL of the uploaded image is then inserted into the 'file' column of the 'feed' table in the database, along with the other parameters.
    
    If the 'url' parameter is not present, the 'file' column is left empty.
    
    After inserting the image URL into the database, the function redirects the user to their profile page.
    
    Returns:
    - If the image is successfully saved and inserted into the database, the function redirects the user to their profile page.
    - If the 'url' parameter is not present, the function redirects the user to the 'dalle' route.
    """
    if request.method == 'POST':
        image_url = request.form.get("url")
        user_id = request.form.get("user_id")
        category = request.form.get("category")
        paste_prompt = request.form.get("paste_prompt")
        print(request.form.get("url"))
        chunk = ''

        if image_url:
            # Download the image from the URL
            response = requests.get(image_url)

            if response.status_code == 200:
                # Open the downloaded image using Pillow
                image = Image.open(io.BytesIO(response.content))

                # Compress the image while trying to maintain quality and target size
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

                # Save the compressed image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                    temp_file.write(buffer.getvalue())

                s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
                image_filename = secure_filename(unique_filename)

                # Upload the temporary file to S3
                s3.upload_file(temp_file.name, BUCKET_NAME, image_filename)

                # Get the S3 URL for the uploaded image file
                image_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{image_filename}"
                file_path = image_s3_url

                # Delete the temporary file
                os.remove(temp_file.name)
            else:
                return redirect(url_for('dalle'))
        else:
            file_path = ""


        # Insert the image URL into the database
        cursor = mysql.connection.cursor()
        text = unidecode.unidecode(paste_prompt).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        cursor.execute("INSERT INTO feed (file, title, user_id, chunk, category, created_at, slug) VALUES (%s, %s, %s, %s, %s, NOW(), %s)", (file_path, paste_prompt, user_id, chunk, category, slug))
        mysql.connection.commit()
        cursor.close()

        flash('You have posted successfully', 'success')

        return redirect(url_for('profile', user_id=user_id))


    return redirect(url_for('dalle'))


@app.route("/generate_img1", methods=['POST'])
def generate_img1():
    """
    Generates an image using the DALL-E 2 model from OpenAI based on the provided prompt.
    
    This function is a route handler for the '/generate_img1' endpoint, which is accessed via a POST request.
    It expects a form field named 'paste_prompt' in the request body.
    
    Parameters:
        None
    
    Returns:
        A JSON response containing a list of dictionaries. Each dictionary contains a single key-value pair,
        where the key is 'url' and the value is the URL of the generated image.
    """
    prompt = request.form["paste_prompt"]

    if request.method == 'POST':
        print('generating image')
        imageResponse = openaiClient.images.generate(
            model="dall-e-2",
            prompt=prompt,
            n=4,
            size="1024x1024",
        )

        response = []

        for x in imageResponse.data:
            response.append({
                'url': x.url
            })
        

    # Return the image URL as a JSON response
    return jsonify(response)


# @app.route('/stream')
# def stream():
#     return render_template('stream.html')


# @socketio.on('ask_openai')
# def handle_message(message):
#     question = message['question']
#     response = openai.Completion.create(engine="text-davinci-003", prompt=question, max_tokens=150)
#     full_answer = response.choices[0].text.strip()
    
#     # Split answer into words or tokens
#     tokens = full_answer.split()
    
#     streamed_answer = ""
#     for token in tokens:
#         streamed_answer += token + " "
#         socketio.emit('answer_chunk', {'answer_chunk': streamed_answer})
#         time.sleep(0.1)  # delay of 0.1 second between tokens


# Define route "/api".
@app.route('/api/', methods=['GET'])
def api():
    """
    A route that handles GET requests to the '/api/' endpoint.

    Returns:
        The rendered template 'image-edit.html'.
    """
    return render_template('image-edit.html')


# Define route "/api/request to openai".
@app.route('/api/generate/', methods=['POST'])
def openai_api():
    """
    This function handles POST requests to the '/api/generate/' endpoint. It receives an image, a mask, and a prompt as form data. 

    Parameters:
    - image (str): The base64-encoded image data.
    - mask (str): The base64-encoded mask data.
    - prompt (str): The prompt for the image generation task.

    Returns:
    - dict: A JSON response containing the generated images. The response has the following structure:
        {
            'images': List[str]
        }
        - images (List[str]): A list of base64-encoded image data.

    Note:
    - This function decodes the base64-encoded image and mask data, compresses the image data, and then runs the image editing task using the provided prompt.
    - The image editing task is performed asynchronously using the 'tasks.run_image_edit_task' function.
    """
    image = request.form['image']
    mask = request.form['mask']
    prompt = request.form['prompt']

    # Decode the base64-encoded image data
    decoded_image_data = base64.b64decode(image)
    result = compress_image_png(decoded_image_data, 3*1024)

    # Decode the base64-encoded image data
    decoded_image_data = base64.b64decode(image)
    result = compress_image_png(decoded_image_data, 3*1024)

    # Decode the base64-encoded mask data
    decoded_mask_data = base64.b64decode(mask)
    mask_result = compress_image_png(decoded_mask_data, 3*1024, result[1])
    imageResponse = tasks.run_image_edit_task(result[0], mask_result[0], prompt)
    return jsonify({'images': imageResponse})


@app.route('/api/post_image', methods=['POST'])
def post_image_to_database():
    """
    Handles the POST request to '/api/post_image' route and saves the image to an S3 bucket.
    
    Parameters:
    - None
    
    Returns:
    - If the image is successfully posted to the database and saved to S3, returns a JSON response with the message 'Image posted to the database and saved to S3 successfully'.
    - If there is an error during the process, returns a JSON response with the error message.
    
    Note:
    - This function retrieves the image URL and prompt from the request data.
    - If the image URL is provided, it downloads the image from the URL, compresses it, saves it to a temporary file, and uploads it to an S3 bucket.
    - The image URL is then inserted into the database along with the prompt, user ID, chunk, and a unique slug.
    - If the image URL is not provided, the file path is set to an empty string.
    - The function uses the boto3 library to interact with the S3 bucket.
    - The function uses the unidecode library to convert the prompt to lowercase and remove special characters.
    - The function uses the re library to replace non-alphanumeric characters in the prompt with underscores.
    - The function uses the datetime library to generate a unique timestamp for the slug.
    - The function uses the mysql-connector-python library to interact with the MySQL database.
    - The function returns a JSON response with the appropriate message or error.
    """
    try:
        # Get the image URL from the request data
        image_url = request.form.get('image_url')
        prompt = request.form.get('prompt')
        user_id = session['user_id']
        chunk = ''
        
        if image_url:
            # Download the image from the URL
            response = requests.get(image_url)

            if response.status_code == 200:
                # Open the downloaded image using Pillow
                image = Image.open(io.BytesIO(response.content))

                # Compress the image while trying to maintain quality and target size
                max_size_kb = 50  # Target size in KB
                quality = 95  # Initial quality
                buffer = io.BytesIO()
                while True:
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=quality)
                    if buffer.getbuffer().nbytes < max_size_kb * 1024 or quality <= 10:
                        break
                    quality -= 5

                unique_filename = f"p2s-{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"

                # Save the compressed image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                    temp_file.write(buffer.getvalue())

                s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
                image_filename = secure_filename(unique_filename)

                # Upload the temporary file to S3
                s3.upload_file(temp_file.name, BUCKET_NAME, image_filename)

                # Get the S3 URL for the uploaded image file
                image_s3_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{image_filename}"
                file_path = image_s3_url

                # Delete the temporary file
                os.remove(temp_file.name)
            else:
                return jsonify({'error': 'Failed to download the image from the URL'})
        else:
            file_path = ""

        # Insert the image URL into the database
        cursor = mysql.connection.cursor()
        text = unidecode.unidecode(prompt).lower()
        slug = re.sub(r'[\W_]+', '_', text)
        slug = str((datetime.now() - datetime(1970, 1, 1)).total_seconds()) + '_' + slug
        cursor.execute("INSERT INTO feed (file, title, user_id, chunk, created_at, slug) VALUES (%s, %s, %s, %s, NOW(), slug)", (file_path, prompt, user_id, chunk, slug))
        mysql.connection.commit()
        cursor.close()

        return jsonify({'message': 'Image posted to the database and saved to S3 successfully'})

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/download', methods=['GET'])
def download_image():
    """
    Downloads an image from the provided URL and compresses it while maintaining quality and target size.
    
    :return: A Flask response object containing the compressed image as an attachment. If the image download fails, a JSON error message is returned.
    :rtype: flask.Response or flask.jsonify
    """
    image_url = request.args.get("image_url")

    response = requests.get(image_url)
    if response.status_code == 200:
        filename = uuid.uuid4().hex + '.png'
        # Open the downloaded image using Pillow
        image = Image.open(io.BytesIO(response.content))

        # Compress the image while trying to maintain quality and target size
        max_size_kb = 50  # Target size in KB
        quality = 95  # Initial quality
        buffer = io.BytesIO()
        while True:
            image.save(buffer, format="JPEG", quality=quality)
            if buffer.getbuffer().nbytes < max_size_kb * 1024 or quality <= 10:
                break
            quality -= 5
            # Save the compressed image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(buffer.getvalue())

            response = send_file(temp_file.name, mimetype='image/png', as_attachment=True, download_name=filename)
            # Delete the temporary file
            
            temp_file.close()
            # os.remove(temp_file.name)
    else:
        return jsonify({'error': 'Failed to download the image from the URL'})
    
    if not image_url:
        return "URL parameter is missing", 400

    return response
    # Fetch the image from the provided URL
    # response = requests.get(image_url)
    
    # # Check if the request was successful
    # if response.status_code == 200:
    #     # Convert the response content to a BytesIO object
    #     image_data = BytesIO(response.content)
        
    #     # Send the image as an attachment
    #     response = send_file(image_data, mimetype='image/png', as_attachment=True, download_name='downloaded_image.png')
    #     return response

    # else:
    #     return "Image not found", 404


# ------------------Contact us----------------------
@app.route('/contact-us', methods=['GET'])
def contact():
   """
   A route that handles GET requests to '/contact-us' and renders the 'contact.html' template.

   Returns:
       A rendered template for the 'contact.html' page.
   """
   return render_template('contact.html')


@app.route('/report_post/<int:post_id>', methods=['POST'])
def report_post(post_id):
    """
    Handles POST requests to '/report_post/<int:post_id>' and reports a post for review.

    Args:
        post_id (int): The ID of the post to be reported.

    Returns:
        flask.Response: A redirect to the 'feed' page with a success flash message if the post is reported successfully.
                        Otherwise, a redirect to the 'feed' page with an error flash message.

    Raises:
        None

    Description:
        This function is a route handler for POST requests to '/report_post/<int:post_id>'. It retrieves the user ID from the session,
        gets the reason for reporting the post from the request form, and then inserts the report into the 'report_post' table in the database.
        If the post with the given ID does not exist, it flashes an error message and redirects to the 'feed' page. Otherwise, it flashes a success message
        and redirects to the 'feed' page.
    """
    user = session.get('user_id')

    # form detail
    reason = request.form.get('reason')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM feed WHERE id = %s', (post_id,))
    post = cursor.fetchone()

    if not post:
        flash('Error while reporting post', 'error')
        return redirect(url_for('feed'))
    
    cursor.execute('INSERT INTO report_post (user_id, post_id, reason) VALUES (%s, %s, %s)', (user, post_id, reason))
    mysql.connection.commit()

    flash('You have reported post for review.', 'success')
    return redirect(url_for('feed'))
    pass

# block user
@app.route('/block-user/<user_id>', methods=['POST'])
def block_user(user_id):
    """
    Route for blocking a user.
    
    This route handles the POST request to block a user. It takes in the user_id as a parameter and retrieves the current user's ID from the session. It then checks if the user exists in the database and if not, it flashes an error message and redirects to the user's profile page. 
    
    If the user exists, it checks if the current user has already blocked the user. If so, it deletes the entry from the blocked_user table. If not, it inserts a new entry into the blocked_user table and removes the user from the current user's circle (if exists). 
    
    After the blocking/unblocking process, it flashes a success message and redirects to the feed page.
    
    Parameters:
        user_id (str): The ID of the user to be blocked.
    
    Returns:
        flask.Response: The response object that redirects to the feed page.
    """
    currentUserId = session.get('user_id')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # check if user exists
    cursor.execute('SELECT * FROM user WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()

    if not user:
        flash('Error while blocking user', 'error')
        return redirect(url_for('profile', user_id=user_id))

    cursor.execute('SELECT * FROM blocked_user WHERE user_id = %s AND blocked_user_id = %s', (currentUserId,user_id))
    blocked = cursor.fetchone()
    if blocked:
        cursor.execute('DELETE FROM blocked_user WHERE user_id = %s AND blocked_user_id = %s',(currentUserId,user_id))
        mysql.connection.commit()
    else:
        cursor.execute('INSERT INTO blocked_user (user_id, blocked_user_id) VALUES (%s, %s)',(currentUserId,user_id))
        mysql.connection.commit()
        # Remove user from circle if exists
        cursor.execute('DELETE FROM follows WHERE follower_id = %s AND following_id = %s',(currentUserId,user_id))
        mysql.connection.commit()

    flash('You have blocked user - ' + user['name'] + '', 'success')
    return redirect(url_for('feed'))

if __name__ == "__main__":
    app.run()
