import pandas
import glob
from jinja2 import Environment, FileSystemLoader
from definitions import data_path, default_speech_file, s3_speech_path
from s3 import s3
from voice import voice
from configs import configs


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
