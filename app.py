import os
from flask import Flask, render_template
from flask.ext.socketio import SocketIO
from jarvis.event_handler import EventHandler

app = Flask(__name__)
app.config.from_object(os.environ.get('APP_SETTINGS'))
socket = SocketIO(app)


@app.route('/')
def index():
	return render_template('index.html')


@socket.on('event', namespace = '/master')
def new_event(event):
	EventHandler(event).handle_event()
	

if __name__ == '__main__':
	socket.run(app, port = 3000, debug = app.config.get('DEBUG'))
