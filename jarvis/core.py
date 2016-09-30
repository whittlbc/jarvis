from flask.ext.socketio import emit


class Jarvis(object):
	formulas = {}

	def listen(self, pattern, flags = 'i'):
		def decorator(f):
			self.formulas[pattern] = { 'flags': flags, 'cb': f }
			return f
		
		return decorator

	def respond(self, text):
		emit('response', { 'text': text })
		
		
class CoreEvent(object):
	
	def __init__(self, type, text, pattern, matches):
		self.type = type
		self.text = text
		self.pattern = pattern
		self.matches = matches