from flask import Flask, render_template, Response
import requests
import json
import sseclient

app = Flask(__name__)

 
API_KEY = '############################'


def performRequestWithStreaming():
    reqUrl = 'https://api.openai.com/v1/completions'
    reqHeaders = {
        'Accept': 'text/event-stream',
        'Authorization': 'Bearer ' + API_KEY
    }
    reqBody = {
      "model": "text-davinci-003",
      "prompt": "What is Python?",
      "max_tokens": 100,
      "temperature": 0,
      "stream": True,
    }
    request = requests.post(reqUrl, stream=True, headers=reqHeaders, json=reqBody)
    client = sseclient.SSEClient(request)
    for event in client.events():
        if event.data != '[DONE]':
            print(json.loads(event.data)['choices'][0]['text'], end="", flush=True),


if __name__ == "__main__":
    performRequestWithStreaming()


#------------render data from openai and save to history----------
@app.route('/feed_generate', methods=['POST'])
def feed_generate():  
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

        if num_submissions >= 100:
            # Disable form after 10 submissions
            session[form_disabled_key] = True

        form_disabled = session.get(form_disabled_key, False)

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