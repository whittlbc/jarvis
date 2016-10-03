from jarvis import jarvis


# Basic interactions: ---------------------------------

@jarvis.listen(['hey jarvis', 'hey', 'hi', 'jarvis', 'hello'])
def hey(event):
	jarvis.respond('Hey man!')
	

@jarvis.listen(['what\'s up', 'what up', 'whats up'])
def whats_up(event):
	jarvis.respond('Not much, homie.')
	
	
@jarvis.listen(['who am i', 'what\'s my name', 'whats my name', 'what my name'])
def user_name(event):
	# name = db.get('user', 'name')
	jarvis.respond('You\'re Ben.')
	

@jarvis.listen(['weather'])
def weather(event):
	jarvis.respond('Weather info')
