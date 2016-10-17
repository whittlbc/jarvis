from jarvis.core.message import Message
from jarvis import logger, predictor
import jarvis.actions.errors as errors
import jarvis.actions.core as core
import jarvis.helpers.helpers as helpers
import jarvis.helpers.db as db
import re


def perform(e):
	user_input = e['text']
	
	# Create an Event class with our known event data
	message = Message(e['text'])
	
	# Do nothing if empty text
	if not message.text.strip(): return
	
	# Run through our registered text matches, regex patterns, etc.
	# before using our trained model to make the prediction
	if matches_text_pattern(message): return
			
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
		

def matches_text_pattern(m):
	potential_matches = [
		fetch_memory,
		new_memory,
		forget_memory,
		wrong_answer,
		selecting_action_from_list
	]
	
	for pm in potential_matches:
		if pm(m): return True
		
	return False


def fetch_memory(m):
	m = re.search('(what is|what\'s) (.*)', m.text, re.I)
	if not m: return False
	
	mem_key = m.group(2).strip().lower()
	
	# remove question mark if user added that
	if mem_key.endswith('?'):
		mem_key = mem_key[:-1]
	
	mem_val = db.fetch_memory(mem_key)
	if not mem_val: return False
	
	core.remember(mem_val)
	
	return True
	

def new_memory(m):
	m = re.search('remember (.*) (as|is) (.*)', m.text, re.I)
	if not m: return False
	
	# Figure out what x and y are from: '... remember x as|is y...'
	x, y = m.group(1).strip(), m.group(3).strip()
	
	if x.startswith('that '): x = x[5:]
	if y.endswith('.'): y = y[:-1]
	
	# Return if either are empty strings
	if not x or not y: return False
	
	# Add memory to DB
	db.new_memory(x.lower(), y)
	
	core.resp_new_memory(x, y)
	
	return True
	

def forget_memory(m):
	m = re.search('forget (.*)', m.text, re.I)
	if not m: return False
	
	x = m.group(1).strip()
	if x.endswith('.'): x = x[:-1]
	
	if not x or not db.forget_memory(x.lower()): return False
	
	core.forget(x)
	
	return True
	

def wrong_answer(m):
	# Is the user correcting Jarvis?
	if m.clean_text == 'wrong':
		# Save user message
		db.save_message({'text': m.text, 'isAudio': False})
		
		# Tell jarvis to prompt you with list of actions so the user can
		# tell him what he should've done.
		correct_jarvis(m, 'response:incorrect')
		return True

	return False
	

def selecting_action_from_list(m):
	text_is_int = True
	text = m.clean_text
	
	# Check if text can be represented as an integer.
	try:
		text = int(text)
	except ValueError:
		text_is_int = False

	# If text isn't an integer representation, return.
	if not text_is_int: return False
	
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
		db.save_message({'text': m.text, 'isAudio': False})
		
		# Perform the correct action on the previous command.
		run_action(action, message)
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
