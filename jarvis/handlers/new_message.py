from jarvis.core.event import Event
from jarvis import logger, predictor
import jarvis.actions.errors as errors


def perform(e):
	user_input = e['text']
	
	# Create an Event class with our known event data
	event = Event(e['type'], e['text'])
	
	# If user typed, 'wrong', prompt the user to help correct Jarvis.
	if event.text.lower().strip() == 'wrong':
		correct_jarvis(event, 'response:incorrect')
		return
	
	# Load the model if it hasn't already been loaded.
	predictor.load_model()
	
	# Predict an action to perform based on the user's input.
	action = predictor.predict(user_input)
	
	# Action is only returned if it's confidence is >=0.5
	if action:
		# Log the user input and which action was predicted.
		logger.info('User Input: {}; Predicted Action: {}'.format(user_input, action))
		
		# From our 'module:method' syntax for actions, access this method from this method and call it.
		module_name, method_name = action.split(':')
		module = user = __import__('jarvis.actions.{}'.format(module_name), globals(), locals(), ['object'], -1)
		method = getattr(module, method_name)
		method(event)
	else:
		correct_jarvis(event, 'confidence:low')


def correct_jarvis(e, reason):
	logger.info('Correcting Jarvis for reason: {}'.format(reason))
	errors.list_actions(e, reason)
