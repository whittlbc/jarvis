from jarvis.core.event import Event
from jarvis import logger, predictor
import jarvis.actions.errors as errors
import jarvis.helpers.helpers as helpers
import jarvis.helpers.db as db


def perform(e):
	user_input = e['text']
	
	# Create an Event class with our known event data
	event = Event(e['type'], e['text'])
	
	# Do nothing if empty text
	if not event.text.strip(): return
	
	# Check for any direct text matches that should take precedent over the trained model.
	if is_direct_text_match(event): return
		
	# Load the model if it hasn't already been loaded.
	predictor.load_model()
	
	# Predict an action to perform based on the user's input.
	action = predictor.predict(user_input)
	
	# Save user message
	db.save_message({'text': event.text, 'isAudio': False}, is_command=True)
	
	# Action is only returned if it's confidence is >=0.5
	if action:
		# Log the user input and which action was predicted.
		logger.info('User Input: {}; Predicted Action: {}'.format(user_input, action))
		
		run_action(action, event)
	else:
		correct_jarvis(event, 'confidence:low')


def is_direct_text_match(e):
	text = e.text.lower().strip()
	
	# Is the user correcting Jarvis?
	if text == 'wrong':
		# Save user message
		db.save_message({'text': text, 'isAudio': False})
		
		# Tell jarvis to prompt you with list of actions so the user can
		# tell him what he should've done.
		correct_jarvis(e, 'response:incorrect')
		return True
	
	if user_selecting_action(text):
		return True
	
	return False


def user_selecting_action(text):
	textIsInt = True
	
	# Check if text can be represented as an integer.
	try:
		text = int(text)
	except ValueError:
		textIsInt = False

	# If text isn't an integer representation, return.
	if not textIsInt: return False
	
	num = text
	
	# If we got an int from the text, see if it can be used an an action index.
	actions = helpers.get_actions()
	
	# If the number is in the range of the number of actions + the ignore option...
	if num > 0 and num <= (len(actions) + 1):
		# Move on if Jarvis wasn't prompting you to correct him with his last message.
		if not helpers.prev_msg_was_correct_jarvis(): return False
		
		# If the 'Ignore' option was selected, do nothing.
		if num is (len(actions) + 1): return True
		
		# Get the action the user selected.
		action = actions[num - 1]
		event = helpers.last_command_event()
		
		# If no previous command event in memory, move on.
		if not event: return False
		
		# Save user message
		db.save_message({'text': text, 'isAudio': False})
		
		# Perform the correct action on the previous command.
		run_action(action, event)
		
		# Good to save this event text to the file with name = action.
		
		return True
	else:
		return False
		

def run_action(action, e):
	module_name, method_name = action.split(':')
	module = user = __import__('jarvis.actions.{}'.format(module_name), globals(), locals(), ['object'], -1)
	method = getattr(module, method_name)
	method(e)
	

def correct_jarvis(e, reason):
	logger.info('Correcting Jarvis for reason: {}'.format(reason))
	errors.list_actions(e, reason)
