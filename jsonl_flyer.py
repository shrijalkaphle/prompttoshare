import pandas as pd

df = pd.read_csv('profession.csv')
df.to_json('profession.json', orient='records', lines=True)
import json

with open('profession.json', 'r') as f:
    data = json.load(f)

for d in data:
    d['prompt'] = f"I am a {d['grade']} with a passion for {d['passion']} and earning {d['earnings']} as a {d['type']}."
    d['completion'] = d['profession']
    del d['grade']
    del d['passion']
    del d['earnings']
    del d['type']
    del d['profession']

with open('profession.jsonl', 'w') as f:
    for d in data:
        f.write(json.dumps(d) + '\n')
