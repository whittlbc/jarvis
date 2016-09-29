from jarvis.handlers import new_message, user_connect


class EventHandler(object):
	
	RESPONSE_MAP = {
		'message:new': new_message,
		'user:connect': user_connect
	}
	
	def __init__(self, event):
		self.event = event
		self.type = event['type']
		
	def handle_event(self):
		handler = self.RESPONSE_MAP[self.type]
		handler.perform(self.event)
