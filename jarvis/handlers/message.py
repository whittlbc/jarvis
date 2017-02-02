import apiai
from jarvis.helpers.configs import config
from jarvis.core.response import Response
from jarvis import request_helper

ai = apiai.ApiAI(config('APIAI_CLIENT_ACCESS_TOKEN'))


def get_response(e):
	query = e['text']
	
	# Ensure query isn't blank
	if not query.strip(): return
	
	# Step 1: Convert query(string) to intent(JSON) -- user-defined formulas take priority.
	intent = intent_from_formula(query) or intent_from_api(query)
	if not intent: return
	
	# Step 2: Convert intent to performable actions
	actions = intent_to_actions(intent)
	
	# Need to figure out how to perform each action and then return a Response object if that was an action
	return None


def intent_from_formula(query=''):
	return None


def intent_from_api(query=''):
	request = ai.text_request()
	request.session_id = request_helper.gen_session_token()
	request.query = query
	return request.getresponse().read()


def intent_to_actions(intent):
	return []