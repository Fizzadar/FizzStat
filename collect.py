#!/usr/bin/env python

# FizzStat
# File: collect.py
# Desc: tiny Flask app to server collect JS & collect stats

import json
import logging
from io import open
from hashlib import md5
from datetime import datetime
from urlparse import urlparse

from flask import Flask, Response, request, abort
from redis import Redis

import settings


# Generate date for Elasticsearch
def _isodate():
    return datetime.now().replace(microsecond=0).isoformat()

# Load JS into string/cache
js = None
def _js():
    global js
    if js:
        return js

    str = open('collect.py.js', 'r').read()
    if not settings.DEBUG:
        js = str

    return str


# Stuff to init upon server boot
logger = redis = None
def boot():
    global redis, logger

    # Init logging
    logger = logging.getLogger('fizzstat')
    logging.basicConfig(level=(logging.DEBUG if settings.DEBUG else logging.WARNING))

    # Init Redis
    logger.debug('Connecting to Redis...')
    redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


# Make the app
app = Flask('FizzStat-Collect', static_folder='')
app.debug = settings.DEBUG

# The main route
@app.route('/', methods=['GET'])
def collect():
    # Referrer & host are required (no point loading this page direct!)
    referrer = request.headers.get('Referer')
    host = request.headers.get('Host')
    if not referrer or not host:
        return abort(400)

    # Is referrer a valid host?
    urlbits = urlparse(referrer)
    if '*' not in settings.ALLOWED_HOSTS and urlbits.hostname not in settings.ALLOWED_HOSTS:
        return abort(400)

    # Basic client details we can get from any request
    hash_data = {
        'ip': request.remote_addr,
        'browser': request.headers.get('User-Agent', 'Unknown'),
        'accept': request.headers.get('Accept', 'Unknown'),
        'language': request.headers.get('Accept-Language', 'Unknown'),
        'encoding': request.headers.get('Accept-Encoding', 'Unknown'),
        'client_hash': request.args.get('client_hash', '')
    }

    # Key to identify users (not guaranteed unique, but pretty good)
    client_key = md5(json.dumps(hash_data)).hexdigest()
    iso_date = _isodate()
    # Key to identify *this* page view
    view_key = md5('{0}{1}'.format(client_key, iso_date)).hexdigest()

    # Data to -> Redis
    redis_data = {
        'url': referrer,
        'datetime': iso_date,
        'view_key': view_key,
        'client_key': client_key,
        'client_data': {
            'ip': hash_data['ip'],
            'browser': hash_data['browser'],
            'hash': hash_data['client_hash']
        }
    }
    redis.lpush('fizzstat_views', json.dumps(redis_data))
    logger.debug('+View on client {0}: {1}'.format(client_key, referrer))

    return Response(
        status=200,
        content_type='text/javascript',
        response=_js().format(('true' if settings.DEBUG else 'false'), host, client_key, view_key)
    )

# Additional events
@app.route('/event/<view_key>/<event_type>', methods=['POST', 'OPTIONS'])
def event(view_key, event_type):
    # For checking allowed hosts
    referrer = request.headers.get('Referer')
    if not referrer:
        return abort(400)

    # Is referrer a valid host?
    urlbits = urlparse(referrer)
    if '*' not in settings.ALLOWED_HOSTS and urlbits.hostname not in settings.ALLOWED_HOSTS:
        return abort(400)

    # OPTIONS just to get origin control working, POST for actual event
    if request.method == 'POST':
        # Must have JSON data
        if not request.json:
            return abort(400)
        # Must also have a value
        value = request.json.get('value')
        if not value:
            return abort(400)

        # Data to -> Redis
        redis_data = {
            'datetime': _isodate(),
            'view_key': view_key,
            'event_type': event_type,
            'value': request.json['value'],
            'data': request.json.get('data')
        }
        redis.lpush('fizzstat_events', json.dumps(redis_data))
        logger.debug('+Event on view {0}: {1}/{2}'.format(view_key, event_type, request.json['value']))

    return Response(
        status=200,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        }
    )


# Hook uwsgi
try:
    import uwsgi
    uwsgi.post_fork_hook = boot
except ImportError:
    pass

# Dev mode
if __name__ == '__main__':
    boot()
    app.run()
