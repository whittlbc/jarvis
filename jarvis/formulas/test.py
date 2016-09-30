from jarvis import jarvis


@jarvis.listen('test')
def time(event):
	jarvis.respond('Heard testing')