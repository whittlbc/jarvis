from jarvis import app
from flask import render_template, request
# import jarvis.learn.classify.train as trainer
from flask.ext.socketio import SocketIO
# from jarvis.handlers import new_message
from jarvis.helpers.configs import configs
# import jarvis.jobs as jobs
from jarvis.helpers.cache import cache

socket = SocketIO(app)
namespace = '/master'


@app.route('/')
def index():
	return render_template('index.html')


# Set up socket listeners:
@socket.on('connect', namespace=namespace)
def on_connect():
	app.logger.info('New User Connection')
	# cache.set('user_sid', request.sid)


@socket.on('disconnect', namespace=namespace)
def on_disconnect():
	app.logger.info('User Disconnected')
	# cache.delete('user_sid')


@socket.on('message', namespace=namespace)
def on_message(e):
	print "\nHEARD NEW MESSAGE: {}\n".format(e['text'])
	# new_message.perform(e)

	
# Train our classifier
# trainer.perform()

# Add jobs to our scheduler
# jobs.add_jobs(app)

# Start our app
if __name__ == '__main__':
	socket.run(app, port=3000, debug=configs.DEBUG, use_reloader=False)