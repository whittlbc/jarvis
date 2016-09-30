from jarvis import jarvis


@jarvis.listen('fuck you')
def fuck_you(event):
	jarvis.respond('Fuck you too')