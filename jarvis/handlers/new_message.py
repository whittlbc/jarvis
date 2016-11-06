from jarvis.core.message import Message
from jarvis import logger, predictor
from jarvis.learn.converse.rnn import Rnn
import jarvis.actions.errors as errors
import jarvis.actions.core as core
import jarvis.helpers.helpers as helpers
import jarvis.helpers.db as db
import re

rnn = Rnn()


def perform(e):
	message = Message(e)
	
	# Do nothing if empty text
	if not message.text.strip(): return
	
	# Run through our registered text matches, regex patterns, etc.
	# before using our trained model to make the prediction
	if matches_text_pattern(message): return
			
	# Load the model if it hasn't already been loaded.
	predictor.load_model()
	
	# Predict an action to perform based on the user's input.
	action, confident_enough = predictor.predict(message.text)
	
	# Save user message in persistent mongodb
	db.save_message({'text': message.text, 'isAudio': False}, is_command=True)
	
	logger.info("User Input: {};\nPredicted Action: {}".format(message.text, action))
	
	# Only perform the predicted action if the model was confident enough
	if confident_enough:
		run_action(action, message)
		
	# Otherwise, default to our conversational model to respond
	else:
		action = ''  # we don't want to update the message cache with an incorrect action...
		converse(message)

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
	wh = ['who', 'what', 'when', 'where']
	patterns = []
	
	for w in wh:
		patterns += ['{} is'.format(w), '{}\'s'.format(w), '{} are'.format(w)]
		
		if w in ['who', 'what']:
			patterns.append('{}\'re'.format(w))
		
	patterns = '({}) (.*)'.format('|'.join(patterns))
	
	matches = re.search(patterns, m.text, re.I)
	if not matches: return False
	
	wh = matches.group(1).lower()
	attr_type = re.sub(r'( is|\'s| are|\'re)', '', wh)
	
	mem_key = matches.group(2).strip().lower()
	
	if mem_key[-1] in ('.', '?', '!'):
		mem_key = mem_key[:-1]

	memory = db.get_memory(mem_key, attr_type)
	
	if not memory: return False
	core.remember(memory, m.is_audio)
	
	return True


def new_memory(m):
	pos = ['is', 'are', 'was', 'will be']
	preps = ['on', 'in', 'at']
	patterns = []
	
	for p in pos:
		patterns += ([p + ' {}'.format(prep) for prep in preps] + [p])
		
	patterns = '|'.join(['as'] + patterns)
	
	matches = re.search('(remember that|remember) (.*) ({}) (.*)'.format(patterns), m.text, re.I)
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
	core.resp_new_memory(memory, verb_phrase, attr_value, m.is_audio)
	
	# Add memory to DB
	db.update_memory(memory, attr_type, attr_value)
	
	return True
	

def get_attr_type(m, memory, verb_phrase):
	if verb_phrase[-3:] == ' on':
		attr_type = 'when'
	elif verb_phrase[-3:] == ' in':
		attr_type = 'where'
	elif m.is_person(memory.lower()):
		attr_type = 'who'
	else:
		attr_type = 'what'
		
	return attr_type


def forget_memory(m):
	matches = re.search('forget (.*)', m.text, re.I)
	if not matches: return False
	
	x = matches.group(1).strip()
	if x.endswith('.'): x = x[:-1]
	
	if not x or not db.forget_memory(x.lower()): return False
	
	core.forget(x, m.is_audio)
	
	return True
	

def list_memories(m):
	if m.clean_text != 'memories': return False
	core.list_memories(db.get_memories(), m.is_audio)
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
	if 0 < num <= (len(actions) + 1):
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
		

# Perform action predicted by trained classifier
def run_action(action, m):
	module_name, method_name = action.split(':')
	module = __import__('jarvis.actions.{}'.format(module_name), globals(), locals(), ['object'], -1)
	method = getattr(module, method_name)
	method(m)
	

# Use trained seq2seq rnn to predict what Jarvis should say
def converse(m):
	response = rnn.predict(m.text)
	core.trained_chat_resp(response, m.is_audio)
	
	
def correct_jarvis(m, reason):
	logger.info('Correcting Jarvis for reason: {}'.format(reason))
	errors.list_actions(m, reason)
