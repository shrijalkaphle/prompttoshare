import csv
import json

csv_file = 'profession.csv'
jsonl_file = 'profession.jsonl'

with open(csv_file) as f:
    reader = csv.DictReader(f)
    with open(jsonl_file, 'w') as out:
        for row in reader:
            data = {}
            data['prompt'] = f"Grade: {row['grade']}, Passion: {row['passion']}, Earning: {row['earning']}, Type: {row['type']}"
            data['completion'] = row['profession']
            out.write(json.dumps(data) + '\n')
