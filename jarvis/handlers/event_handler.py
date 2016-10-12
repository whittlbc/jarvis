from jarvis.handlers import new_message, user_connect


class EventHandler(object):
	
	HANDLER_MAP = {
		'message:new': new_message,
		'user:connect': user_connect
	}
	
	def __init__(self, event):
		self.event = event
		self.type = event['type']
		
	def handle_event(self):
		handler = self.HANDLER_MAP[self.type]
		handler.perform(self.event)
