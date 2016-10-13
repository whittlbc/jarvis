from jarvis.core.event import Event
import jarvis.actions as actions
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
	
	# Perform our predicted action, passing in our event
	action_method = getattr(actions, action)
	action_method(event)
