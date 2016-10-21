import pandas
import glob
from jinja2 import Environment, FileSystemLoader
from definitions import data_path, default_speech_file, s3_speech_path
from s3 import s3
from voice import voice
from configs import configs
from jarvis.core.message import Message
import db as db


def render_temp(file, **kwargs):
	env = Environment(loader = FileSystemLoader('templates'))
	template = env.get_template(file)
	return template.render(**kwargs)


def get_actions():
	actions = []
	
	for csv in csvs():
		action = read_csv(csv).values[:, 1][0]
		actions.append(action)
		
	actions.sort()
	return actions
	

def csvs():
	return glob.glob(data_path + "/*.csv")


def read_csv(f, sep='|'):
	return pandas.read_csv(f, sep=sep, header=None)


def tts(text):
	with open(default_speech_file, 'w+') as audio_file:
		with voice.use_ogg_codec():
			voice.fetch_voice_fp(text, audio_file)

	s3.upload_file(default_speech_file, configs.S3_BUCKET_NAME, s3_speech_path)


# get latest message from jarvis and see if it has 'correctMe' == True
def prev_msg_was_correct_jarvis():
	# Get Jarvis' oid from his user record
	jarvis_oid = db.oid(db.get_jarvis())
	
	# Get all messages from jarvis
	last_jarvis_msg = db.messages().find({'user_oid': jarvis_oid}).sort([('ts', -1)]).limit(1)
	
	if last_jarvis_msg.count() == 0: return False
	
	return last_jarvis_msg[0]['correctMe'] is True
	

# Get an event object for the last user command
def last_command_msg():
	# Get user's oid from his user record
	user_oid = db.oid(db.current_user())

	# Find the last user command message
	msg = db.messages().find({'user_oid': user_oid, 'isCommand': True}).sort([('ts', -1)]).limit(1)
	
	if msg.count() == 0: return None
	
	return Message(msg[0]['text'])


def perspective_swap(text):
	swap_map = {
		'my': 'your',
		'your': 'my',
		'mine': 'yours',
		'yours': 'mine'
	}
	
	words = []

	for word in text.split(' '):
		word = swap_map.get(word) or word
		words.append(word)
	
	return ' '.join(words)