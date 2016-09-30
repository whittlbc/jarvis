from jarvis import jarvis


@jarvis.listen('test')
def time(event):
	jarvis.respond('Test Heard. Here are your matches: {}'.format(event.matches))
