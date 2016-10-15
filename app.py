from jarvis import app
import jarvis.learn.train as trainer
from jarvis.helpers import helpers
from flask.ext.socketio import SocketIO
import jarvis.handlers.event_handler as event_handler
from jarvis.helpers.configs import configs


socket = SocketIO(app)


# Set up HTTP routes
@app.route('/')
def index():
	return helpers.render_temp('index.html')


# Set up socket listeners
@socket.on('event', namespace='/master')
def new_event(e):
	event_handler.handle_event(e)
	
	
# Train our NN
trainer.perform()


# Start our app
if __name__ == '__main__':
	socket.run(app, port=3000, debug=configs.DEBUG)

