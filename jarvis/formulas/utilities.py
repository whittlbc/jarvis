from jarvis import jarvis


@jarvis.listen('hey jarvis')
def hey(event):
	jarvis.respond('Hey man!')
	

@jarvis.listen(['what\'s up', 'what up', 'whats up'])
def whats_up(event):
	jarvis.respond('Not much, homie.')
