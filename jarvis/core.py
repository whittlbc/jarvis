from flask.ext.socketio import emit


class Jarvis(object):
	formulas = {}


	def listen(self, pattern):
		def decorator(f):
			self.formulas[pattern] = f
			return f
		
		return decorator
	
	
	def respond(self, text):
		emit('response', { 'text': text })
		
		
class CoreEvent(object):
	
	def __init__(self, type, text, pattern, match):
		self.type = type
		self.text = text
		self.pattern = pattern
		self.match = match