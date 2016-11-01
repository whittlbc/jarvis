from jarvis.core.responder import respond
import jarvis.helpers.helpers as helpers


def list_actions(m, reason):
	count = 1
	actions = helpers.get_actions() + ['Ignore']
	text = "{}\n".format(reason_for_listing_actions(reason))
	
	for action in actions:
		text += "\n({}) {}".format(count, action)
		count += 1
		
	respond(text, correct_me=True)
	

def reason_for_listing_actions(reason):
	return {
		'confidence:low': 'Not sure about that one...which action did you want?',
		'response:incorrect': 'I\'m sorry, Ben. What should I have done?'
	}[reason]