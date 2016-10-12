from jarvis import jarvis
from jarvis.helpers import db

# Basic interactions: ---------------------------------

@jarvis.listen(['hey jarvis', 'hey', 'hi', 'jarvis', 'hello'])
def hey(e):
	jarvis.respond('Hey man!')
	

@jarvis.listen(['what\'s up', 'what up', 'whats up'])
def whats_up(e):
	jarvis.respond('Not much, homie.')
	

@jarvis.listen(['who am i', 'what\'s my name', 'whats my name', 'what my name'])
def user_name(e):
	current_user = db.current_user()
	jarvis.respond('You\'re {}'.format(current_user['name']))
	

@jarvis.listen(['[^ \w]+'])
def weather(e):
	jarvis.respond('Weather info')
