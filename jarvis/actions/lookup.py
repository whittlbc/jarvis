from jarvis.core.responder import respond


def google(query, is_audio=False):
	answer = None
	respond(answer, with_audio=is_audio)