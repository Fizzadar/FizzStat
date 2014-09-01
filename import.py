#!/usr/bin/env python

# FizzStat
# File: import.py
# Desc: reads stats from Redis, processes & imports to Elasticsearch

import sys
import json
import logging
from time import sleep
from urlparse import urlparse

from redis import Redis
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

import settings


# Stuff to init
logger = redis = es = None

# Import views to Elasticsearch
def import_view(json_data):
    data = json.loads(json_data)
    logger.debug('+View on client {0}: {1}'.format(data['client_key'], data['url']))

    # Check if the client exists
    try:
        es.get(index='fizzstat', doc_type='client', id=data['client_key'])
    except NotFoundError:
        # Add the client
        logger.debug('Client not found, adding {0}'.format(data['client_key']))
        es.index(index='fizzstat', doc_type='client', id=data['client_key'], body={
            'ip': data['client_data']['ip'],
            'browser': data['client_data']['browser'],
            'hash': data['client_data']['hash']
        })

    # Parse the url
    urlbits = urlparse(data['url'])
    port = urlbits.port
    if not port:
        if urlbits.scheme == 'http':
            port = 80
        elif urlbits.scheme == 'https':
            port = 433

    # Add the view
    es.index(index='fizzstat', doc_type='view', id=data['view_key'], body={
        'client': data['client_key'],
        'date': data['datetime'],
        'url': data['url'],
        'host': urlbits.hostname,
        'port': port,
        'path': urlbits.path,
        'query': urlbits.query
    })

# Import events to Elasticsearch
def import_event(json_data):
    data = json.loads(json_data)
    logger.debug('+Event on view {0}: {1}/{2}'.format(data['view_key'], data['event_type'], data['value']))

    # Check the view exists
    try:
        result = es.get(index='fizzstat', doc_type='view', id=data['view_key'])
        view = result['_source']
    except NotFoundError:
        logger.warning('Invalid event on non-existant view: {0}'.format(data['view_key']))
        return

    # Add the event
    es.index(index='fizzstat', doc_type='event', body={
        'client': view['client'],
        'view': data['view_key'],
        'date': data['datetime'],
        'type': data['event_type'],
        'value': data['value'],
        'data': data['data']
    })


if __name__ == '__main__':
    # Init logging
    logger = logging.getLogger('fizzstat')
    logging.basicConfig(level=(logging.DEBUG if settings.DEBUG else logging.WARNING))

    # Init Redis
    logger.debug('Connecting to Redis...')
    redis = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)

    # Init Elasticsearch
    logger.debug('Connecting to Elasticsearch...')
    es = Elasticsearch(settings.ES_NODES, timeout=10)

    # The loop
    logger.debug('Starting loop...')
    try:
        while True:
            # Views always before events
            view = redis.rpop('fizzstat_views')
            if view:
                import_view(view)
            else:
                # Events
                event = redis.rpop('fizzstat_events')
                if event:
                    import_event(event)

            if not view:
                logger.debug('No views or events, sleeping for {0}s'.format(settings.IMPORT_INTERVAL))
                sleep(settings.IMPORT_INTERVAL)
    except KeyboardInterrupt:
        logger.debug('Exiting on ctrl+c')
        sys.exit(0)
