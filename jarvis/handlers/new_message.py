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
	action, confident_enough = predictor.predict(user_input)
	
	# Save user message in persistent mongodb
	db.save_message({'text': message.text, 'isAudio': False}, is_command=True)
	
	logger.info("User Input: {};\nPredicted Action: {}".format(user_input, action))
	
	if confident_enough:
		run_action(action, message)
	else:
		action = ''
		chat_response(message)

	# Cache command message in redis
	db.update_msg_cache(message.text, action)


def matches_text_pattern(m):
	potential_matches = [
		fetch_memory,
		new_memory,
		forget_memory,
		list_memories,
		airhorn,
		echo,
		wrong_answer,
		selecting_action_from_list
	]
	
	for pm in potential_matches:
		if pm(m): return True
		
	return False


def fetch_memory(m):
	matches = re.search('(what is|what\'s|who is|who\'s|where is|where\'s|when is|when\'s) (.*)', m.text, re.I)
	if not matches: return False
	
	wh = matches.group(1).lower()
	
	if wh == 'who is' or wh == 'who\'s':
		attr_type = 'who'
	elif wh == 'what is' or wh == 'what\'s':
		attr_type = 'what'
	elif wh == 'when is' or wh == 'when\'s':
		attr_type = 'when'
	elif wh == 'where is' or wh == 'where\'s':
		attr_type = 'where'
	
	mem_key = matches.group(2).strip().lower()
	
	if mem_key[-1] in ('.', '?', '!'):
		mem_key = mem_key[:-1]

	memory = db.get_memory(mem_key.lower(), attr_type)
	
	if not memory: return False
	core.remember(memory)
	
	return True
	

def new_memory(m):
	matches = re.search(
		'(remember that|remember) (.*) (as|is on|is in|is at|is|was on|was in|was at|was|will be on|will be in|will be at|will be) (.*)',
		m.text,
		re.I
	)
	
	if not matches: return False
	
	memory = matches.group(2).strip()
	verb_phrase = matches.group(3)
	
	# Decide what attribute type is being defined about the memory: who, what, when, or where.
	attr_type = get_attr_type(m, memory, verb_phrase)
	attr_value = matches.group(4).strip()
	
	if not attr_value: return False
	
	if attr_value[-1] in ('.', '?', '!'):
		attr_value = attr_value[:-1]
	
	# Respond
	core.resp_new_memory(memory, verb_phrase, attr_value)
	
	# Add memory to DB
	db.update_memory(memory, attr_type, attr_value)
	
	return True
	

def get_attr_type(m, memory, verb_phrase):
	when_where_map = {
		'is on': 'when',
		'was on': 'when',
		'will be on': 'when',
		'is at': 'where',
		'was at': 'where',
		'will be at': 'where',
		'is in': 'where',
		'was in': 'where',
		'will be in': 'where'
	}
	
	attr_type = when_where_map.get(verb_phrase)
	
	if attr_type: return attr_type  # when or where
	if m.is_person(memory): return 'who'
	return 'what'


def forget_memory(m):
	matches = re.search('forget (.*)', m.text, re.I)
	if not matches: return False
	
	x = matches.group(1).strip()
	if x.endswith('.'): x = x[:-1]
	
	if not x or not db.forget_memory(x.lower()): return False
	
	core.forget(x)
	
	return True
	

def list_memories(m):
	if m.clean_text != 'memories': return False
	core.list_memories(db.get_memories())
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
	
	
def airhorn(m):
	m = re.search('(airhorn|air horn)', m.text, re.I)
	if not m: return False
	
	from jarvis.actions.random import airhorn_resp
	airhorn_resp(m)
	
	return True


def echo(m):
	if m.clean_text.startswith('echo '):
		from jarvis.actions.random import echo_resp
		echo_resp(m)
		return True


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
		
		# Update the last_command message (that is currently being corrected) in Redis
		# to have the proper action.
		db.update_last_command_action(action)
		
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


def chat_response(m):
	# use trained LSTM model to predict what Jarvis should say
	response = 'Predicted response'
	core.trained_chat_resp(response)