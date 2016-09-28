import os
from flask import Flask
from flask import jsonify
from flask import request
from functools import wraps
from utils import logger

# Create Flask app
app = Flask(__name__)

# import config vars
app.config.from_object(os.environ['APP_SETTINGS'])

# Create logger: (Ex: logger.info, logger.warning, logger.error)
logger = logger.get_logger(app)


# Home page route
@app.route('/')
def index():
	return "Home"


# Another route
@app.route('/<name>')
def my_name(name):
	return "Hey there {}!".format(name)


# JSON route
@app.route('/new')
def new_route():
	response = jsonify({ 'key': 'val' })
	return response


# Route with multiple methods:
@app.route('/multi_method', methods = ['GET', 'POST'])
def multi_method():
	if request.method == 'GET':
		return get_resp()
		
	elif request.method == 'POST':
		return "Heard Post"


def get_resp():
	return "Heard Get"


def before_filter(f):
	return f
	
	
def check_auth(username, password):
	return username == 'admin' and password == 'secret'


def authenticate():
	message = { 'message': "Authenticate." }
	resp = jsonify(message)

	resp.status_code = 401
	resp.headers['WWW-Authenticate'] = 'Basic realm="Example"'

	return resp


def auth_before_filter(f):
	# Wrap the original function with this "decorated" one.
	@wraps(f)
	def decorated(*args, **kwargs):
		auth = request.authorization
		
		if not auth:
			return authenticate()
		
		elif not check_auth(auth.username, auth.password):
			return authenticate()
		
		return f(*args, **kwargs)
	
	return decorated


# Route with before filters
@app.route('/with_before_filter')
@before_filter
@auth_before_filter
def with_before_filter():
	return "All good."


if __name__ == '__main__':
	app.run(port = 3000, debug = app.config['DEBUG'])
