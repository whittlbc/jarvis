import db as db


def name():
	user = db.current_user()
	return user['name']


def first_name():
	return name().split(' ')[0]
