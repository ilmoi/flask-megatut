import json
import os
import uuid
import requests

from app import app


def translate(text, source_language, dest_language):
    # decided to hardcode destination language, as was having trouble

    if 'MS_TRANSLATOR_KEY' not in app.config or not app.config['MS_TRANSLATOR_KEY']:
        return 'Error: no trans key'

    subscription_key = os.environ.get('MS_TRANSLATOR_KEY')
    endpoint = "https://api.cognitive.microsofttranslator.com/"
    path = '/translate?api-version=3.0'
    params = f'&from={source_language}&to=en'
    constructed_url = endpoint + path + params

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4()),
        'Ocp-Apim-Subscription-Region': 'westeurope'
    }

    body = [{
        'text': text
    }]

    r = requests.post(constructed_url, headers=headers, json=body)

    if r.status_code != 200:
        return 'translation failed'
    return json.loads(r.content.decode('utf-8-sig'))[0]['translations'][0]['text']