import logging
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from jarvis.helpers.request_helper import RequestHelper
from jarvis.helpers.configs import config
# from jarvis.core.predictor import Predictor

# Init app
app = Flask(__name__)

# Add app logger
app.logger.addHandler(logging.FileHandler('main.log'))
app.logger.setLevel(logging.INFO)
logger = app.logger

# predictor = Predictor()

# Set up DB
app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

request_helper = RequestHelper(app)

db = SQLAlchemy(app)

# import our models
from models import User, Session



