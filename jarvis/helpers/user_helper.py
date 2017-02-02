from definitions import session_header


def set_current_user(req):
	session_token = req.headers.get(session_header)
	
	if not session_token:
		print 'Invalid User Permissions'
		return None
	
	# TODO: Find user through Session.user_id where Session.token=session_token
	return {'uid': 'abc123'}