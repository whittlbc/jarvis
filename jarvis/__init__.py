import os
import logging
import redis
from flask import Flask
from jarvis.core import Jarvis

# Init app
app = Flask(__name__)

# Set up app configs
app.config.from_object(os.environ.get('APP_SETTINGS'))

# Add app logger
app.logger.addHandler(logging.FileHandler('main.log'))
app.logger.setLevel(logging.INFO)

# Store redis singleton instance on app
app.redis = redis.StrictRedis.from_url(app.config.get('REDIS_URL'))

jarvis = Jarvis()