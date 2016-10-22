from flask.ext.socketio import emit
from jarvis.helpers.helpers import tts
import jarvis.helpers.db as db


def respond(text, with_audio=True, data=None, correct_me=False):
	# Upload the text as audio if specified
	# if with_audio:
		# tts(text)
	
	# Data to be sent back to client
	message = {
		'text': text,
		'isAudio': with_audio,
		'data': data
	}
	
	# Respond to the client
	emit('response', message)
	
	# Store message in db
	db.save_message(message, from_jarvis=True, correct_me=correct_me)