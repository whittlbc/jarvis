import apiai
from jarvis.helpers.configs import config
from jarvis import request_helper, logger
from db_helper import where
from models import Formula, UserFormula
from jarvis.helpers.formulas_helper import find_matching_formula
from jarvis.actions import klass_method_for_action
from definitions import unknown_action
import json


ai = apiai.ApiAI(config('APIAI_CLIENT_ACCESS_TOKEN'))


def get_response(e, user):
	intent = e.get('intent', {})
	params = intent.get('params', {})
	user_metadata = e.get('userMetadata', {})
	# query = intent.get('resolvedQuery', '')
	#
	# if not query.strip(): return None
	#
	# # Priority 1: See if any user-defined formulas are triggered by this query
	# formula_ids = [uf.formula_id for uf in where(UserFormula, {'user_id': user.id})]
	#
	# if formula_ids:
	# 	formula_uids = [f.uid for f in where(Formula, {'id': formula_ids})]  # prolly should order by created_by as well
	#
	# 	# Grab the first Formula class that is triggered by this query (if any)
	# 	matching_formula = find_matching_formula(formula_uids, query)
	#
	# 	# Execute the formula's "triggered" callback
	# 	if matching_formula:
	# 		matching_formula.perform()
	#
	# 		return matching_formula.respond()  # should return Response object
		
	# Priority 2: See if any core actions are triggered by this query
	intent['action'] = 'weather.search'
	
	action_klass, action_method = klass_method_for_action(intent.get('action'))
	
	if action_klass and action_method:
		action_instance = action_klass(params, user, user_metadata, with_voice=e.get('withVoice'))
		return getattr(action_instance, action_method)()
	
	return None


# Only used for python fetching of api.ai info (switched to Swift)

# def intent_from_api(query=''):
# 	request = ai.text_request()
# 	request.session_id = request_helper.gen_session_token()
# 	request.query = query
# 	return request.getresponse().read()
#
#
# def action_from_intent(intent):
# 	result = None
#
# 	try:
# 		json_intent = json.loads(intent) or {}
# 		result = json_intent.get('result')
# 	except:
# 		logger.error('Error parsing JSON response from API.ai')
#
# 	if result:
# 		return result.get('action'), result.get('parameters')
#
# 	return None, None