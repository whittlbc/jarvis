import os
import json
from jarvis import app
from jarvis import request_helper as rh
from flask import request
from flask_socketio import SocketIO
from jarvis.helpers.configs import config
from jarvis.handlers.message import get_response
from jarvis.handlers.connections import connect, disconnect
from definitions import cookie_name, session_header
import jarvis.helpers.error_codes as ec
from db_helper import find, create
from models import User, Session

socket = SocketIO(app)
namespace = '/master'


# ---- HTTP Routes ----

def get_current_user(req):
	session_token = req.headers.get(session_header)
	if not session_token: raise Exception()
	
	session = find(Session, {'token': session_token})
	if not session: raise Exception()
	
	return find(User, {'id': session.user_id})
	

def strip_creds_from_req(data):
	creds = json.loads(data) or {}
	return creds.get('email', '').strip(), creds.get('password', '').strip()


@app.route('/signup', methods=['POST'])
def signup():
	email, pw = strip_creds_from_req(request.data)
	
	if not email or not pw:
		return rh.error(**ec.INCOMPLETE_LOGIN_CREDS)
	
	user = find(User, {'email': email})
	if user: return rh.error(**ec.EMAIL_TAKEN)
	
	try:
		user = create(User, {'email': email, 'password': pw})
		session = create(Session, {'user_id', user.id})
		return rh.json_response(with_cookie=(cookie_name, session.token))
	except Exception as e:
		app.logger.error('Error signing up new user with email: {}, with error: {}'.format(email, e))
		return rh.error(**ec.USER_SIGNUP_ERROR)


@app.route('/login', methods=['POST'])
def login():
	email, pw = strip_creds_from_req(request.data)
	
	if not email or not pw:
		return rh.error(**ec.INCOMPLETE_LOGIN_CREDS)
	
	user = find(User, {'email': email, 'password': pw})
	if not user: return rh.error(**ec.USER_NOT_FOUND)
	
	try:
		session = create(Session, {'user_id', user.id})
		return rh.json_response(with_cookie=(cookie_name, session.token))
	except Exception as e:
		app.logger.error('Error logging in existing user with email: {}, with error: {}'.format(email, e))
		return rh.error(**ec.USER_LOGIN_ERROR)


# ---- Socket Listeners ----

@socket.on('connect', namespace=namespace)
def on_connect():
	app.logger.info('New User Connection')
	
	try:
		user = get_current_user(request)
	except Exception:
		return rh.error(**ec.INVALID_USER_PERMISSIONS)
	
	connect(request.sid, user)
	

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
	resp = get_response(e)
	
	if resp:
		socket.emit('response', resp.as_json(), namespace=namespace)


# Add jobs to our scheduler (Need to do this in a user-specific way)
# jobs.add_jobs(app)

if __name__ == '__main__':
	socket.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=config('DEBUG'), use_reloader=False)
