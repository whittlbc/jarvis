from jarvis.actions import klass_method_for_action


def get_response(e, user):
	intent = e.get('intent', {})
	action_klass, action_method = klass_method_for_action(intent.get('action'))
	
	if action_klass and action_method:
		action_instance = action_klass(
			query=intent.get('query'),
			params=intent.get('params'),
			user=user,
			user_metadata=e.get('userMetadata'),
			with_voice=e.get('withVoice')
		)
		
		return getattr(action_instance, action_method)()
	
	return None