from jarvis import jarvis


@jarvis.listen('/time/')
def time(event):
	# event is CoreEvent instance
	jarvis.respond('Time is 1:43: {}'.format(event.match))
