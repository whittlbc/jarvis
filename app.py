import os
from definitions import model_path
from jarvis import app
from jarvis.helpers import helpers
from flask.ext.socketio import SocketIO
import jarvis.handlers.event_handler as event_handler
import jarvis.learn.train as trainer

socket = SocketIO(app)


# Set up HTTP routes
@app.route('/')
def index():
	return helpers.render_temp('index.html')


# Set up socket listeners
@socket.on('event', namespace='/master')
def new_event(e):
	event_handler.handle_event(e)
	
	
# Train and save our NN if it doesn't exist yet
if not os.path.isfile(model_path):
	trainer.perform()


# Start our app
if __name__ == '__main__':
	socket.run(app, port=3000, debug=app.config.get('DEBUG'))

