class Event:
	
	def __init__(self, type, text, pattern, matches):
		self.type = type
		self.text = text
		self.pattern = pattern
		self.matches = matches
