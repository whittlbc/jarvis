from jarvis.core.responder import respond
import jarvis.helpers.greeting as g


def greeting(m):
	respond(g.random_greeting())