import os
import json
from jarvis import app, request_helper
from flask import request
from flask_socketio import SocketIO
from jarvis.helpers.configs import config
from jarvis.handlers.message import get_response
from jarvis.handlers.connections import connect, disconnect
from definitions import cookie_name, session_header
from jarvis.helpers.user_helper import set_current_user


socket = SocketIO(app)
namespace = '/master'


# ---- HTTP Routes ----

@app.route('/signup', methods=['POST'])
def signup():
	creds = json.loads(request.data) or {}
	email = creds.get('email', '').strip()
	password = creds.get('password', '').strip()
	
	if not email or not password:
		return request_helper.error('Invalid Credentials', 500)
	
	# (1) find_or_initialize_by new user with email(unique) and password
	# error out if email already in use
	# if email not taken yet --> good, create a new session with user_id=<new_user.id>
	# add newly-created session token as a cookie and return it that way
	
	token = request_helper.gen_session_token()  # hard-coding for now. TODO: pull this from newly-created Session record.
	
	return request_helper.json_response(with_cookie=(cookie_name, token))


@app.route('/login', methods=['POST'])
def login():
	creds = json.loads(request.data) or {}
	email = creds.get('email', '').strip()
	password = creds.get('password', '').strip()
	
	if not email or not password:
		return request_helper.error('Invalid Credentials', 500)
	
	# Find user by email/password and respond
	# if not user:
	# 	error('User not found', 404)
		
	token = request_helper.gen_session_token()  # hard-coding for now. TODO: pull this from newly-created Session record.

	return request_helper.json_response(with_cookie=(cookie_name, token))


# ---- Socket Listeners ----

@socket.on('connect', namespace=namespace)
def on_connect():
	app.logger.info('New User Connection')
	user = set_current_user(request)
	
	if not user:
		print 'User not found for session token'
		return request_helper.error('Can\'t connect socket - invalid user session', 403)
	
	connect(request.sid, user)
	

@socket.on('disconnect', namespace=namespace)
def on_disconnect():
	app.logger.info('User Disconnected')
	user = set_current_user(request)
	
	if user:
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
