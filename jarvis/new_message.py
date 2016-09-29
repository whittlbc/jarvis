from flask.ext.socketio import emit

def perform(event):
	emit('response', { 'text': event['text'] })