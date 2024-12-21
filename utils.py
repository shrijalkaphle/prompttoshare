import requests

"""
    Saves an image from the given URL to a local file.

    Args:
        url (str): The URL of the image to be saved.
        filename (str): The name of the local file to save the image to.

    Returns:
        None

    Raises:
        Exception: If an error occurs while saving the image.

    This function downloads an image from the given URL and saves it to a local file. It uses the `requests` library to make the HTTP request and write the response content to the file. If the request is successful, the function prints a message indicating that the image was saved successfully. If the request fails, the function prints an error message indicating the URL that failed. If an exception occurs during the process, the function prints an error message with the exception details.
"""
def save_image_locally(url, filename):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(filename, 'wb') as file:
                file.write(response.content)
            print(f"Image saved as {filename}")
        else:
            print(f"Failed to download image from URL: {url}")
    except Exception as e:
        print(f"An error occurred while saving the image: {str(e)}")