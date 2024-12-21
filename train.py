import openai
import json

openai.api_key = "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"

model_engine = 'text-davinci-002'

training_data = []

with open('profession.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        training_data.append(data)

prompt = training_data[0]['prompt']

openai.Completion.create(
    engine=model_engine,
    prompt=prompt,
temperature=0,
            max_tokens=100,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["\n"]
)