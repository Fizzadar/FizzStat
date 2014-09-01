# FizzStat
# File: settings.py
# Desc: the... settings

ALLOWED_HOSTS = [
    '*'
]

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

ES_NODES = [
    'localhost:9200'
]

IMPORT_INTERVAL = 15

DEBUG = False

# Get optional custom settings
try:
    from settings_ext import *
except ImportError:
    pass
