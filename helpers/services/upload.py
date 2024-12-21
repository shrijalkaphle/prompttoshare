import os
import threading
import uuid
import boto3


BUCKET_NAME = 'ai-interf-social'
AWS_ACCESS_KEY_ID = '########################################'
AWS_SECRET_ACCESS_KEY = 

def uploadUserProfile(image):
    
    imageName = str(uuid.uuid4()) + '.jpg'
    image.save(imageName)
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    s3.upload_file(imageName, BUCKET_NAME, imageName)
    os.remove(imageName)
    return f"https://ai-interf-social.s3.amazonaws.com/{imageName}"