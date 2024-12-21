import base64
import uuid
import os
from PIL import Image

target_size_kb = 4096

def base64_to_img(data):
    imgdata = base64.b64decode(data)
    filename = str(uuid.uuid4()) +'.png'
    with open(filename, 'wb') as f:
        f.write(imgdata)

    # resizing image
    resizedFilename = str(uuid.uuid4()) +'.png'
    resize_and_compress_image(filename, resizedFilename)
    return resizedFilename

def make_image_transparent(imgstring):
    imgdata = base64.b64decode(imgstring)
    filename = str(uuid.uuid4()) +'.png'
    with open(filename, 'wb') as f:
        f.write(imgdata)

    # convert image to RGBA
    # img = Image.open(filename)
    # img = img.convert("RGBA")
    # datas = img.getdata()

    # newData = []
    # for item in datas:
    #     if item[0] == 255 and item[1] == 238 and item[2] == 255:
    #         newData.append((255, 255, 255, 0))
    #     else:
    #         newData.append(item)
    # img.putdata(newData)
    updatedFilename = str(uuid.uuid4()) +'.png'
    # img.save(updatedFilename, "PNG")
    # os.remove(filename)
    
    return updatedFilename

def make_mask_image(mask, original):
    # create an image overlaping mask
    filename = 'imgwithmask.png'
    image = Image.open(original)
    overlay = Image.open(mask)
    image.paste(overlay, (0,0), mask = overlay)
    image.save(filename)
    overlay.close()
    image.close()

    # delete image with only mask
    os.remove(mask)

    # make the mask component transparent
    img = Image.open(filename)
    img = img.convert("RGBA")
    datas = img.getdata()
    newData = []
    for item in datas:
        if item[0] == 255 and item[1] == 238 and item[2] == 255:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    img.putdata(newData)
    updatedFilename = str(uuid.uuid4()) +'.png'
    img.save(updatedFilename, "PNG")
    img.close()

    # # delete old image
    os.remove(filename)
    return updatedFilename

def resize_and_compress_image(original, resizedFilename):
    # Open the image using Pillow
    image = Image.open(original)
    resized_image = image.resize((1024, 1024), Image.ANTIALIAS)
    resized_image.save(resizedFilename)
    image.close()
    os.remove(original)
    return resized_image


    # Calculate the resize ratio based on current size and target
    ratio = (target_size_kb * 1024 / len(original)) ** 0.5

    # Start compressing
    while True:
        # Resize the image
        new_dimensions = (int(image.width * ratio), int(image.height * ratio))
        image = image.resize(new_dimensions)

        output_io = io.BytesIO()
        image.save(output_io, format="PNG")

        if output_io.getbuffer().nbytes < target_size_kb * 1024:
            break