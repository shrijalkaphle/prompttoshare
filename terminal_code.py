


#1 works in master terminal #
 curl https://api.openai.com/v1/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer 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" \
-d '{"model": "text-davinci-003", "prompt": "Say this is a test", "temperature": 0, "max_tokens": 7}'
# response is: {"id":"cmpl-6kZTcgipFFtzwcJriKpDdBrmWqP1a","object":"text_completion","created":1676557480,"model":"text-davinci-003","choices":[{"text":"\n\nThis is indeed a test","index":0,"logprobs":null,"finish_reason":"length"}],"usage":{"prompt_tokens":5,"completion_tokens":7,"total_tokens":12}}


#2 works in master terminal
 curl https://api.openai.com/v1/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer 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" \
-d '{"model": "text-davinci-003", "prompt": "Is this is a test?", "temperature": 0, "max_tokens": 20}'
# response is: {"id":"cmpl-6kaYbbzZU2nWlLX2NM0YtRpEaKp1x","object":"text_completion","created":1676561633,"model":"text-davinci-003","choices":[{"text":"\n\nYes, this is a test.","index":0,"logprobs":null,"finish_reason":"length"}],"usage":{"prompt_tokens":6,"completion_tokens":7,"total_tokens":13}}

curl https://api.openai.com/v1/edits \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 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' \
  -d '{
  "model": "text-davinci-edit-001",
  "input": "What day of the wek is it?",
  "instruction": "Fix the spelling mistakes" 
}'
# response is: {"object":"edit","created":1676564433,"choices":[{"text":"What day of the Week is it Sunday?\n","index":0}],"usage":{"prompt_tokens":25,"completion_tokens":29,"total_tokens":54}}

###IMAGE###--START

curl https://api.openai.com/v1/images/generations \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer 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' \
  -d '{
  "prompt": "A cute baby sea puppy",
  "n": 3,
  "size": "1024x1024"
}'

curl https://api.openai.com/v1/embeddings \
  -X POST \
  -H "Authorization: Bearer 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" \
  -H "Content-Type: application/json" \
  -d '{"input": "The food was delicious and the waiter...",
       "model": "text-embedding-ada-002"}'

curl https://api.openai.com/v1/files \
  -H 'Authorization: Bearer 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'

#DSS
curl https://api.openai.com/v1/files \
  -H "Authorization: Bearer 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" \
  -F purpose="fine-tune" \
  -F file='@mydata.jsonl'
