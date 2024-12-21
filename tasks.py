from celery import Celery
from openai import OpenAI
from utils import save_image_locally
import json

CELERY_RESULT_BACKEND = 'rediss://###############################@ec2-44-223-230-57.compute-1.amazonaws.com:16659?ssl_cert_reqs=CERT_NONE'
CELERY_BROKER_URL = 'rediss://###############################@@ec2-44-223-230-57.compute-1.amazonaws.com:16659?ssl_cert_reqs=CERT_NONE'

openaiClient=OpenAI(
    api_key="sk-###############################"
)

# Create a Celery instance
celery = Celery('tasks', backend=CELERY_RESULT_BACKEND, broker=CELERY_BROKER_URL, broker_connection_retry_on_startup=True)


# define class to convert to json
class ImagesResponse:
    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return {'data': self.data}

"""
    Adds two numbers together and returns the result.

    Parameters:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        int: The sum of the two numbers.

    Raises:
        Exception: If the task is forcefully terminated due to a time limit.

    Notes:
        - This function is decorated with the `@celery.task` decorator to make it a Celery task.
        - The `rate_limit` parameter is set to `'1/s'` to limit the task to one execution per second.
        - The `time_limit` parameter is set to `60` seconds to limit the execution time of the task.
        - If the task is forcefully terminated due to the time limit, an `Exception` is raised.
"""
@celery.task(rate_limit='1/s', time_limit=60)
def add_numbers(a, b):
    # raise Exception("Force error!")
    return a+b

"""
Runs an image editing task using OpenAI's API.

Args:
    image (str): The base64-encoded image to edit.
    mask (str): The base64-encoded mask to apply to the image.
    prompt (str): The prompt to provide to the OpenAI API for image editing.

Returns:
    list: A list of dictionaries containing the URLs of the edited images.

Raises:
    Exception: If the task is forcefully terminated due to a time limit.

Notes:
    - This function is decorated with the `@celery.task` decorator to make it a Celery task.
    - The `rate_limit` parameter is set to `'1/s'` to limit the task to one execution per second.
    - The `time_limit` parameter is set to `300` seconds to limit the execution time of the task.
    - If the task is forcefully terminated due to the time limit, an `Exception` is raised.
"""
@celery.task(rate_limit='1/s', time_limit=300)
def run_image_edit_task(image, mask, prompt):
    print('tasks.py: new task is started.')
    imageResponse = openaiClient.images.edit(
            image=image,
            mask=mask,
            prompt=prompt,
            n=4,
            size="1024x1024",
        )

    response = []

    for x in imageResponse.data:
        response.append({
            'url': x.url
        })
        
    return response