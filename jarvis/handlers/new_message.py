from flask.ext.socketio import emit
from jarvis import helpers


def perform(event):
	text = event['text']
	formulas = helpers.registered_formulas()
	text_response('response')


def text_response(text):
	emit('response', { 'text': text })