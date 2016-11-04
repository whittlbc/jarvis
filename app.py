from jarvis import app
from flask import render_template
import jarvis.learn.classify.train as trainer
from flask.ext.socketio import SocketIO
import jarvis.handlers.event_handler as event_handler
from jarvis.helpers.configs import configs


socket = SocketIO(app)


# Set up HTTP routes
@app.route('/')
def index():
	return render_template('index.html')


# Set up socket listeners
@socket.on('event', namespace='/master')
def new_event(e):
	event_handler.handle_event(e)
	

# Train our classifier
trainer.perform()


# Start our app
if __name__ == '__main__':
	socket.run(app, port=3000, debug=configs.DEBUG)

