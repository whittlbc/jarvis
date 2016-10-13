import os
import logging
from flask import Flask
from jarvis.handlers.predictor import Predictor

# Init app
app = Flask(__name__)

# Set up app configs
app.config.from_object(os.environ.get('APP_SETTINGS'))

# Add app logger
app.logger.addHandler(logging.FileHandler('main.log'))
app.logger.setLevel(logging.INFO)
logger = app.logger

predictor = Predictor()