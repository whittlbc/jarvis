from jarvis.core.event import Event
from jarvis import logger, predictor


def perform(e):
	user_input = e['text']
	
	# Load the model if it hasn't already been loaded.
	predictor.load_model()
	
	# Predict an action to perform based on the user's input.
	action = predictor.predict(user_input)
	
	# Log the user input and which action was predicted.
	logger.info('User Input: {}; Predicted Action: {}'.format(user_input, action))
	
	# Create an Event class with our known event data
	event = Event(e['type'], e['text'])
	
	# From our 'module:method' syntax for actions, access this method from this method and call it.
	module_name, method_name = action.split(':')
	module = user = __import__('jarvis.actions.{}'.format(module_name), globals(), locals(), ['object'], -1)
	method = getattr(module, method_name)
	method(event)
