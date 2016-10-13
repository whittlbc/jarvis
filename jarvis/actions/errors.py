from jarvis.core.responder import respond
import jarvis.helpers.helpers as helpers


def low_confidence(e):
	count = 1
	actions = helpers.get_actions() + ['No action']
	text = "Not sure about that one...which action did you want?\n"
	
	for action in actions:
		text += "\n({}) {}".format(count, action)
		count += 1
		
	respond(text)