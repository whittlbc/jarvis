from flask.ext.socketio import emit
import jarvis.helpers.db as db


def respond(text, with_audio=False, data=None, correct_me=False, room=None, navigate_to=None):
	message = {
		'text': text,
		'isAudio': with_audio,
		'navigateTo': navigate_to,
		'data': data
	}
	
	# Respond to the client
	emit('response', message, namespace='/master', room=room)
	
	# Store message in db
	db.save_message(message, from_jarvis=True, correct_me=correct_me)