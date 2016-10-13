from jarvis.handlers import new_message, user_connect

def handle_event(event):
	handler = {
		'message:new': new_message,
		'user:connect': user_connect
	}[event['type']]
	
	handler.perform(event)
