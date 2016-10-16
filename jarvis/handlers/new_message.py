from jarvis.core.message import Message
from jarvis import logger, predictor
import jarvis.actions.errors as errors
import jarvis.helpers.helpers as helpers
import jarvis.helpers.db as db


def perform(e):
	user_input = e['text']
	
	# Create an Event class with our known event data
	message = Message(e['text'])
	
	# Do nothing if empty text
	if not message.text.strip(): return
	
	# Check for any direct text matches that should take precedent over the trained model.
	if is_direct_text_match(message): return
			
	# Load the model if it hasn't already been loaded.
	predictor.load_model()
	
	# Predict an action to perform based on the user's input.
	action, confident = predictor.predict(user_input)
	
	# Save user message in persistent mongodb
	db.save_message({'text': message.text, 'isAudio': False}, is_command=True)
		
	if confident:
		# Log the user input and which action was predicted.
		logger.info('User Input: {}; Predicted Action: {}'.format(user_input, action))
		
		run_action(action, message)
	else:
		correct_jarvis(message, 'confidence:low')
		
	# Cache command message in redis
	db.update_msg_cache(message.text, action)
		

def is_direct_text_match(m):
	text = m.text.lower().strip()
	
	# Is the user correcting Jarvis?
	if text == 'wrong':
		# Save user message
		db.save_message({'text': text, 'isAudio': False})
		
		# Tell jarvis to prompt you with list of actions so the user can
		# tell him what he should've done.
		correct_jarvis(m, 'response:incorrect')
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
		message = helpers.last_command_msg()
		
		# If no previous command event in memory, move on.
		if not message: return False
		
		# Save user message
		db.save_message({'text': text, 'isAudio': False})
		
		# Perform the correct action on the previous command.
		run_action(action, message)
		
		# Good to save this event text to the file with name = action.
		
		return True
	else:
		return False
		

def run_action(action, m):
	module_name, method_name = action.split(':')
	module = user = __import__('jarvis.actions.{}'.format(module_name), globals(), locals(), ['object'], -1)
	method = getattr(module, method_name)
	method(m)
	

def correct_jarvis(m, reason):
	logger.info('Correcting Jarvis for reason: {}'.format(reason))
	errors.list_actions(m, reason)
