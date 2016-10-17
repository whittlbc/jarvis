from jarvis.core.responder import respond
import jarvis.helpers.responses as r


def greeting(m):
	respond(r.random_greeting())


def whatup(m):
	respond(r.random_whatup())


def resp_new_memory(x, y):
	respond('Got it! Remembering {} as {}.'.format(x, y), with_audio=True)


def remember(mem_val):
	respond(mem_val, with_audio=True)