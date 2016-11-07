from jarvis.core.responder import respond
from jarvis.api.google import Google


def google(query):
	top_result = Google().top_result(query)
	respond(None, navigate_to=top_result['link'])