# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gae_flex_quickstart]
import logging
import os

from flask import Flask, request
import json
import requests

from lxml import html
from redis.sentinel import Sentinel

app = Flask(__name__)
_API_KEY = 'AIzaSyDeNOS2U4DxwnhVJvvk6Yd_oV0W19T5unQ'
_XPATH_FOR_META_DESCRIPTION = '//meta[@name="description"]/@content'
_XAPTH_FOR_TITLE = '//title/text()'
_CLOUD_SENTIMENT_API = 'https://language.googleapis.com/v1/documents:analyzeSentiment?key=' + _API_KEY
_POSITIVE_SENTIMENT = 'positive'
_NEGATIVE_SENTIMENT = 'negative'
_NEUTRAL_SENTIMENT = 'neutral'
_REDIS_KEY_PREFIX = 's_'
_redis_client = None


def _get_dom(url):
  page = requests.get(url)
  return html.fromstring(page.content)


def _get_meta_description(dom):
  content_array = dom.xpath(_XPATH_FOR_META_DESCRIPTION)
  if content_array and len(content_array) > 0:
    return content_array[0]
  if not content:
    return ''


def _get_title(dom):
  content_array = dom.xpath(_XAPTH_FOR_TITLE)
  if content_array and len(content_array) > 0:
    return content_array[0]
  if not content:
    return ''


def _get_title_and_desc(dom):
  title = _get_title(dom)
  description = _get_meta_description(dom)
  return title + description
    

def analyze_sentiment(dom):
  content = _get_title_and_desc(dom)
  if not content:
    return {
      'sentiment': _NEUTRAL_SENTIMENT,
      'sentiment_score': 0
    }

  # Make Cloud API call to get sentiment score
  request = {
    'document': {
      'type': 'PLAIN_TEXT',
      'content': content
    },
    'encodingType': 'UTF8'
  }
  try:
    response = requests.post(_CLOUD_SENTIMENT_API, json=request)
    parsed_response = json.loads(response.content)
    sentiment_score = parsed_response['documentSentiment']['score']
    sentiment = None
    if sentiment_score < -0.25:
      sentiment = _NEGATIVE_SENTIMENT
    elif sentiment_score < 0.25:
      sentiment = _NEUTRAL_SENTIMENT
    else:
      sentiment = _POSITIVE_SENTIMENT
    return {
      'sentiment': sentiment,
      'sentiment_score': sentiment_score
    }
  except:
    return {
      'sentiment': _NEUTRAL_SENTIMENT,
      'sentiment_score': 0
    }


def get_key(u):
    return _REDIS_KEY_PREFIX + u


def get_redis_client():
    global _redis_client
    if _redis_client:
        return _redis_client
    sentinel = Sentinel([('10.148.0.6', 26379), ('10.148.0.7',26379), ('10.148.0.8',26379)])
    _redis_client = sentinel.master_for('master')
    return _redis_client


def sentiment(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    # Set CORS headers for the preflight request
    if request.method == 'OPTIONS':
        # Allows GET requests from any origin with the Content-Type
        # header and caches preflight response for an 3600s
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }

        return ('', 204, headers)

    # Set CORS headers for the main request
    headers = {
        'Access-Control-Allow-Origin': '*'
    }
    
    url = request.args.get('u')
    url = url.split('?')[0]
    key = get_key(url)
    print('meetha_Getting data from redis')
    redis_client = get_redis_client()
    response = redis_client.get(key)
    print('meetha_Got data from redis')
    if response:
        return json.dumps(json.loads(response.decode("utf-8")))

    print('meetha_Getting data from webpage')
    dom = _get_dom(url)
    print('meetha_Got data from webpage')
    print('meetha_Getting sentiment')
    sentiment_response = analyze_sentiment(dom)
    print('meetha_Got sentiment')
    response = {
      'sentiment': sentiment_response['sentiment'],
      'sentiment_score': sentiment_response['sentiment_score']
    }
    response = json.dumps(response)
    print('meetha_Setting redis')
    redis_client.set(key, response)
    print('meetha_Set redis done')
    return response


@app.route('/sentiment-analysis')
def sentiment_analysis():
    """Return a friendly HTTP greeting."""
    print('meetha_Request recieved')
    response = sentiment(request)
    print('meetha_Request processed')
    return response


@app.route('/')
def main():
    """Return a friendly HTTP greeting."""
    print('meetha_Request recieved')
    # response = sentiment(request)
    print('meetha_Request processed')
    return 'hello'


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END gae_flex_quickstart]
