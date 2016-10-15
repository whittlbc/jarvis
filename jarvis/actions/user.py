from jarvis.core.responder import respond
import jarvis.helpers.user as user_helper


def name(e):
	respond(user_helper.name(), with_audio=False)
