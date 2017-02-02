import datetime
from jarvis import db, request_helper


class User(db.Model):
	__tablename__ = 'user'
	
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String)
	name = db.Column(db.String)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, email, name):
		self.email = email
		self.name = name
	
	def __repr__(self):
		return '<User(id={}, email={}, name={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.email,
			self.name,
			self.created_at,
			self.is_destroyed
		)
	

class Session(db.Model):
	__tablename_ = 'sessions'
	
	id = db.Column(db.Integer, primary_key=True)
	token = db.Column(db.String, default=request_helper.gen_session_token)
	user_id = db.Column(db.Integer, index=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, user_id):
		self.user_id = user_id
	
	def __repr__(self):
		return '<Session(id={}, token={}, user_id={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.token,
			self.user_id,
			self.created_at,
			self.is_destroyed
		)
