import os
import io
import uuid
from PIL import Image
import multiprocessing
from openai import OpenAI

from helpers.db import execute, fetchAll, fetchOne
from helpers.task import base64_to_img, make_mask_image 

openaiClient=OpenAI(
    api_key="sk-proj-############"
)
MAX_CHARS_PER_CHUNK = 500
MODEL_ENGINE = 'gpt-3.5-turbo'

def openai_processing(animal, model_engine, result_queue):
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
    # chunks = split_text_into_chunks(text, MAX_CHARS_PER_CHUNK)
    
    # Put the result in the queue
    result_queue.put(text)

def generate_feed(animal):
    prompt = f"Write about {animal}"
    return prompt


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
        if int(len(current_chunk) + len(paragraph)) <= int(max_chars_per_chunk):
            current_chunk += paragraph

        #here, the current chunk is added to the chunks list after stripping any leading or trailing whitespace.
        else:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
    
    #if there are remaining chunks left after the loop than than add that to the chunks as well
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def generatePostFeed(user_id, prompt, category):

    # check if generate limit is reached
    generate_limit = fetchOne('SELECT * FROM security')['generate']
    today_generate_count = fetchOne('SELECT count(*) as count FROM history WHERE user_id = '+str(user_id)+' AND DATE(created_at) = CURDATE()')['count']

    
    if int(generate_limit) <= int(today_generate_count):
        return {
            'error': 'Generate limit reached'
        }

    animal = category + " " + prompt
    result_queue = multiprocessing.Queue()
    openai_process = multiprocessing.Process(target=openai_processing, args=(animal, MODEL_ENGINE, result_queue))
    openai_process.start()
    openai_process.join()
    chunks = result_queue.get()
    # execute('INSERT INTO history (title, content, user_id, category) VALUES ('+animal+', '+chunks+', '+user_id+', '+category+')')
    try:
        # add to database
        execute('INSERT INTO history (title, content, user_id, category) VALUES ("'+animal+'", "'+chunks+'", "'+str(user_id)+'", "'+category+'")')
        return {
            'chunks': chunks
        }

    except Exception as e:
            # Handle any database errors here
        return {'error': str(e)}
    
def generateDalleImage(prompt): 
    imageResponse = openaiClient.images.generate(
        model="dall-e-2",
        prompt=prompt,
        n=4,
        size="1024x1024",
    )
    response = []
    for x in imageResponse.data:
        response.append({
            'uri': x.url,
            'id': uuid.uuid1().node
        })
    return response

def editDalleImage(prompt, original, mask):
    #convert base64 to image
    originalFileName = base64_to_img(original)
    onlyMaskFileName = base64_to_img(mask)
    maskFileName = make_mask_image(onlyMaskFileName, originalFileName)

    # open images
    originalFile = open(originalFileName, "rb")
    maskFile = open(maskFileName, "rb")

    imageResponse = openaiClient.images.edit(
        image=originalFile,
        mask=maskFile,
        prompt=prompt,
        n=4,
        size="1024x1024",
    )
    response = []
    for x in imageResponse.data:
        response.append({
            'uri': x.url,
            'id': uuid.uuid1().node
        })

    # delete temp files
    originalFile.close()
    maskFile.close()
    os.remove(originalFileName)
    os.remove(maskFileName)
    return {"data": response}


def compress_image_png(decoded_image_data, target_size_kb=4096, _new_dimensions=(0, 0)):
    # Create an in-memory file for the image
    image_file = io.BytesIO(decoded_image_data)

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

        output_io = io.BytesIO()
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

def getAvailablePrompt():
    return {
        "prompts": fetchAll('SELECT * FROM prompt')
    }