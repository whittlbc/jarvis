from flask.ext.socketio import emit
from jarvis.helpers.helpers import tts


def respond(text, audio=False, data=None):
	# Upload the text as audio if specified
	if audio: tts(text)
	
	message = {
		'text': text,
		'audio': audio,
		'data': data or {}
	}
	
	emit('response', message)

