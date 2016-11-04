import logging
from flask import Flask
from jarvis.core.predictor import Predictor


# Init app
app = Flask(__name__)

# Add app logger
app.logger.addHandler(logging.FileHandler('main.log'))
app.logger.setLevel(logging.INFO)
logger = app.logger

predictor = Predictor()