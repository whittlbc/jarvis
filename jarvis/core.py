from flask.ext.socketio import emit


class Jarvis(object):
	formulas = {}


	def listen(self, patterns, flags = 'i'):
		def decorator(f):
			if isinstance(patterns, (list, tuple)):
				patterns_arr = patterns
			else:
				patterns_arr = [patterns]
				
			for pattern in patterns_arr:
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