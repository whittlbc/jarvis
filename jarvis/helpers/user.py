import db as db


def name(is_jarvis=False):
	if is_jarvis:
		user = db.get_jarvis()
	else:
		user = db.current_user()
		
	return user['name']