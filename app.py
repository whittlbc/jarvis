from jarvis import app
from flask import render_template, request
import jarvis.learn.classify.train as trainer
from flask.ext.socketio import SocketIO
import jarvis.handlers.event_handler as event_handler
from jarvis.helpers.configs import configs
import jarvis.jobs as jobs
from jarvis.helpers.cache import cache

socket = SocketIO(app)


# Set up HTTP routes
@app.route('/')
def index():
	return render_template('index.html')


# Set up socket listeners:
@socket.on('connect', namespace='/master')
def on_connect():
	app.logger.info('New User Connection')
	cache.set('user_sid', request.sid)

	
@socket.on('disconnect', namespace='/master')
def on_disconnect():
	app.logger.info('User Disconnected')
	cache.delete('user_sid')


@socket.on('event', namespace='/master')
def new_event(e):
	event_handler.handle_event(e)

	
# Train our classifier
trainer.perform()

# Add jobs to our scheduler
# jobs.add_jobs(app)

# Start our app
if __name__ == '__main__':
	socket.run(app, port=3000, debug=configs.DEBUG, use_reloader=False)