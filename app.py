import os
import json
from jarvis import app, logger
from jarvis import request_helper as rh
from flask import request, redirect
from flask_socketio import SocketIO
from jarvis.helpers.configs import config
from jarvis.handlers.message import get_response
from jarvis.handlers.connections import connect, disconnect
from definitions import cookie_name, session_header, formula_uploads_path, formula_uploads_module
import jarvis.helpers.error_codes as ec
from jarvis.helpers.s3 import upload
from db_helper import find, create, create_session, find_or_initialize_by, update, destroy_instance
from models import User, Session, Formula, UserFormula, Integration, UserIntegration, PendingRide
from jarvis.helpers.integration_helper import oauth_url_for_integration, uber_auth_flow
from jarvis.helpers.cache import cache
from jarvis.helpers.pending_ride_helper import uber_status_update

socket = SocketIO(app)
namespace = '/master'


# ---- HTTP Routes ----

def parse_req_data(req):
	data = {}
	
	if req.method == 'GET' and req.args:
		data = dict(req.args.items())
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
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)
		
	integration_slug = parse_req_data(request).get('slug')
	
	if not integration_slug:
		return rh.error(message='slug required to identify integration')
	
	integration = find(Integration, {'slug': integration_slug})
	
	if not integration:
		return rh.error(**ec.INTEGRATION_NOT_FOUND)
	
	oauth_url = oauth_url_for_integration(integration, user=user)
	
	if not oauth_url:
		return rh.error(message='Couldn\'t get oauth url for integration with slug: {}'.format(integration_slug))
	
	return rh.json_response(data={'url': oauth_url})


@app.route('/oauth/uber', methods=['GET'])
def uber_oauth_response():
	integration = find(Integration, {'slug': 'uber'})
	
	if not integration:
		return rh.error(**ec.INTEGRATION_NOT_FOUND)
	
	# Parse the state token out of the params (which is the user's uid)
	state_token = parse_req_data(request).get('state')

	# Make sure a user actually exists for this uid...otherwise nothing else matters.
	user = find(User, {'uid': state_token})

	if not user:
		logger.error('User not found for uid: {}'.format(state_token))
		return rh.error(**ec.USER_NOT_FOUND)

	# Finish the OAuth flow by getting a session/access_token for this user
	auth_flow = uber_auth_flow(state_token, integration)
	session = auth_flow.get_session(request.url)
	cred = session.oauth2credential

	ui_unique_params = {
		'user_id': user.id,
		'integration_id': integration.id,
	}
	
	ui_update_params = {
		'access_token': cred.access_token,
		'refresh_token': cred.refresh_token,
		'meta': {
			'expires_in_seconds': cred.expires_in_seconds,
			'grant_type': cred.grant_type
		}
	}

	try:
		find_or_initialize_by(UserIntegration, find_by_params=ui_unique_params, update_params=ui_update_params)
	except Exception as e:
		ui_unique_params.update(ui_update_params)
		logger.error('Error running find_or_initialize for UserIntegration with params {} with error {}'.format(ui_unique_params, e.message))
		return rh.error(message="Error creating/updating UserIntegration instance on Uber OAuth callback")
	
	return redirect("jarvis://")


@app.route('/uber/ride_update', methods=['POST'])
def uber_oauth_response():
	params = parse_req_data(request)
	
	event = params.get('event_type')
	
	if event != 'requests.status_changed':
		logger.error('Unsure how to handle event from Uber: {}'.format(event))
		return rh.json_response()
	
	metadata = params.get('meta') or {}
	external_ride_id = metadata.get('resource_id')
	
	if not external_ride_id:
		logger.error('Couldn\'t find meta.resource_id in params body...: {}'.format(params))
		return rh.json_response()
	
	pending_ride = find(PendingRide, {'external_ride_id': external_ride_id})
	
	if not pending_ride:
		logger.error('No Pending Ride for external_ride_id: {}'.format(external_ride_id))
		return rh.json_response()
		
	user = find(User, {'id': pending_ride.user_id})
		
	if not user:
		logger.error('No User for id: {}'.format(pending_ride.user_id))
		return rh.json_response()

	# Get all socket ids associated with user from cache
	user_sids = cache.hget(config('USER_CONNECTIONS'), user.uid) or []
	
	if not user_sids:
		logger.error('No open sockets registered for user with uid: {}'.format(user.uid))
		return rh.json_response()
	
	status = metadata.get('status')
	status_update = uber_status_update(status)
	
	if not status_update:
		logger.error('No status update could be found for ride status: {}'.format(status))
		return rh.json_response()
	
	# Update the ride even if no need to reach out to user
	logger.info('Updating pending ride with uid {} to status of {}'.format(pending_ride.uid, status))
	update(pending_ride, {'status', status_update['status']})
	
	if status_update.get('destroy_ride'):
		destroy_instance(pending_ride)
	
	response_msg = status_update.get('response')
	
	if response_msg:
		[socket.emit('job:update', {'text': response_msg}, namespace=namespace, room=sid) for sid in user_sids]
	
	return rh.json_response()
	
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
