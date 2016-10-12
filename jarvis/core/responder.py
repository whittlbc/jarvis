from flask.ext.socketio import emit


def respond(data):
	payload = {
		'type': 'text',
		'data': str(data)
	}
	
	if isinstance(data, dict):
		payload['type'] = 'json',
		payload['data'] = data
	
	emit('response', payload)
