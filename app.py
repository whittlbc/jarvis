import os
import json
from jarvis import app, logger
from jarvis import request_helper as rh
from flask import request
from flask_socketio import SocketIO
from jarvis.helpers.configs import config
from jarvis.handlers.message import get_response
from jarvis.handlers.connections import connect, disconnect
from definitions import cookie_name, session_header, formula_uploads_path, formula_uploads_module
import jarvis.helpers.error_codes as ec
from jarvis.helpers.s3 import upload
from db_helper import find, create, create_session
from models import User, Session, Formula, UserFormula, Integration
from jarvis.helpers.integration_helper import oauth_url_for_integration


socket = SocketIO(app)
namespace = '/master'


# ---- HTTP Routes ----

def parse_req_data(req):
	data = {}
	
	if req.method == 'GET' and req.args:
		data = dict(req.args)
	elif req.method != 'GET' and req.data:
		data = json.loads(req.data) or {}

	return data


def get_current_user(req):
	session_token = req.headers.get(session_header)
	if not session_token: raise Exception()
	
	session = find(Session, dict(token=session_token))
	if not session: raise Exception()
	
	return find(User, dict(id=session.user_id))
	

def strip_creds_from_req(data):
	creds = json.loads(data) or {}
	return creds.get('email', '').strip(), creds.get('password', '').strip()


def is_python_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'py'


# This whole thing should prolly be it's own service
def is_valid_formula(filename):
	try:
		formula = __import__('{}.{}'.format(formula_uploads_module, filename), globals(), locals(), ['object'], -1)
	except ImportError as e:
		logger.error('Error importing tmp formula: {}, with error: {}'.format(filename, e.message))
		return False
	
	if not hasattr(formula, 'Formula'):
		logger.error('formula module has no class, Formula, as an attribute.')
		return False
	
	formula_klass = formula.Formula
	
	# Validate the attributes on formula class
	
	return True


@app.route('/signup', methods=['POST'])
def signup():
	email, pw = strip_creds_from_req(request.data)
	
	if not email or not pw:
		return rh.error(**ec.INCOMPLETE_LOGIN_CREDS)
	
	user = find(User, dict(email=email))
	if user: return rh.error(**ec.EMAIL_TAKEN)
	
	try:
		user = create(User, dict(email=email, password=pw))
		session = create(Session, dict(user_id=user.id))
		return rh.json_response(with_cookie=(cookie_name, session.token))
	except Exception as e:
		app.logger.error('Error signing up new user with email: {}, with error: {}'.format(email, e))
		return rh.error(**ec.USER_SIGNUP_ERROR)


@app.route('/login', methods=['POST'])
def login():
	email, pw = strip_creds_from_req(request.data)
	
	if not email or not pw:
		return rh.error(**ec.INCOMPLETE_LOGIN_CREDS)
	
	user = find(User, dict(email=email, password=pw))
	if not user: return rh.error(**ec.USER_NOT_FOUND)
	
	try:
		session = create(Session, dict(user_id=user.id))
		return rh.json_response(with_cookie=(cookie_name, session.token))
	except Exception as e:
		app.logger.error('Error logging in existing user with email: {}, with error: {}'.format(email, e))
		return rh.error(**ec.USER_LOGIN_ERROR)


@app.route('/formula', methods=['POST'])
def new_formula():
	try:
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)
	
	# Ensure there's a file
	file = (request.files or {}).get('file')
	
	if not file:
		return rh.error(**ec.FORMULA_UPLOAD_NO_FILE)

	# Ensure it's a python file
	if not is_python_file(file.filename):
		return rh.error(**ec.FORMULA_UPLOAD_INVALID_FILE_EXT)
	
	# Save file to tmp formula location
	tmp_filename = rh.gen_session_token()
	tmp_filepath = '{}/{}.py'.format(formula_uploads_path, tmp_filename)
	file.save(tmp_filepath)
	
	# Validate the contents of the formula file
	if not is_valid_formula(tmp_filename):
		os.remove(tmp_filepath)
		return rh.error(**ec.INVALID_FORMULA_FORMAT)
	
	# Create new Formula and UserFormula records in the DB
	session = create_session()
	
	try:
		formula = create(Formula, session=session)
		create(UserFormula, {'user_id': user.id, 'formula_id': formula.id, 'is_owner': True}, session=session)
	except Exception as e:
		return rh.error(e.message, 500)
	
	session.commit()
	
	# Upload formula file to S3
	upload(tmp_filepath, '{}/{}.py'.format(config('S3_FORMULAS_DIR'), formula.uid))
	
	# Remove file from tmp directory
	os.remove(tmp_filepath)
	
	return rh.json_response()


@app.route('/integrations/oauth_url', methods=['GET'])
def get_integration_oauth_url():
	try:
		get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)
	
	params = parse_req_data(request)
	integration_slug = (params.get('slug') or [None])[0]
	
	if not integration_slug:
		return rh.error(message='slug required to identify integration')
	
	integration = find(Integration, {'slug': integration_slug})
	
	if not integration:
		return rh.error(**ec.INTEGRATION_NOT_FOUND)
	
	oauth_url = oauth_url_for_integration(integration)
	
	if not oauth_url:
		return rh.error(message='Couldn\'t get oauth url for integration with slug: {}'.format(integration_slug))
	
	return rh.json_response(data={'url': oauth_url})

	
# ---- Socket Listeners ----

@socket.on('connect', namespace=namespace)
def on_connect():
	app.logger.info('New User Connection')
		
	try:
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)
	
	connect(request.sid, user)
	

@socket.on('fetch:user_info', namespace=namespace)
def on_fetch_user_info():
	try:
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)
	
	with open('actions.json') as f:
		resp = {
			'actions': json.load(f),
			'user_name': user.name,
			'bot_name': user.botname
		}
		
		socket.emit('user_info:fetched', resp, namespace=namespace)


@socket.on('disconnect', namespace=namespace)
def on_disconnect():
	app.logger.info('User Disconnected')
	
	try:
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)

	disconnect(request.sid, user)


@socket.on('message', namespace=namespace)
def on_message(e):
	try:
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)

	resp = get_response(e, user)
	
	if resp:
		socket.emit('response', resp.as_json(), namespace=namespace)


# Add jobs to our scheduler (Need to do this in a user-specific way)
# jobs.add_jobs(app)

if __name__ == '__main__':
	socket.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=config('DEBUG'), use_reloader=False)
