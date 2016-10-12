import os
from definitions import model_path
from jarvis import app
from jarvis.helpers import helpers
from flask.ext.socketio import SocketIO
from jarvis.handlers.event_handler import EventHandler
import jarvis.learn.teach as teacher


socket = SocketIO(app)


# Set up HTTP routes
@app.route('/')
def index():
	return helpers.render_temp('index.html')


# Set up socket listeners
@socket.on('event', namespace='/master')
def new_event(event):
	EventHandler(event).handle_event()
	

# Train and save our NN if it doesn't exist yet
if not os.path.isfile(model_path):
	teacher.teach()


# Start our app
if __name__ == '__main__':
	socket.run(app, port=3000, debug=app.config.get('DEBUG'))
