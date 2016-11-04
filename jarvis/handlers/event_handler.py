from jarvis.handlers import new_message


def handle_event(event):
	handler = {
		'message:new': new_message
		# more in future I'm sure
	}[event['type']]
	
	handler.perform(event)