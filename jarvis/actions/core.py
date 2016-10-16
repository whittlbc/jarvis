from jarvis.core.responder import respond
import jarvis.helpers.responses as r


def greeting(m):
	respond(r.random_greeting())


def whatup(m):
	respond(r.random_whatup())
