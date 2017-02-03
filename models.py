import datetime
from jarvis import db, request_helper


class User(db.Model):
	__tablename__ = 'user'
	
	id = db.Column(db.Integer, primary_key=True)
	uid = db.Column(db.String, default=request_helper.gen_session_token)
	email = db.Column(db.String)
	password = db.Column(db.String)
	name = db.Column(db.String)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, email=None, password=None, name=None):
		self.email = email
		self.password = password
		self.name = name
	
	def __repr__(self):
		return '<User(id={}, uid={}, email={}, password={}, name={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.uid,
			self.email,
			self.password,
			self.name,
			self.created_at,
			self.is_destroyed
		)
	

class Session(db.Model):
	__tablename_ = 'session'
	
	id = db.Column(db.Integer, primary_key=True)
	token = db.Column(db.String, default=request_helper.gen_session_token)
	user_id = db.Column(db.Integer, index=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, user_id=None):
		self.user_id = user_id
	
	def __repr__(self):
		return '<Session(id={}, token={}, user_id={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.token,
			self.user_id,
			self.created_at,
			self.is_destroyed
		)


class Formula(db.Model):
	__tablename__ = 'formula'
	
	id = db.Column(db.Integer, primary_key=True)
	uid = db.Column(db.String, default=request_helper.gen_session_token)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self):
		print
	
	def __repr__(self):
		return '<Formula(id={}, uid={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.uid,
			self.created_at,
			self.is_destroyed
		)


class UserFormula(db.Model):
	__tablename__ = 'user_formula'
	
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, index=True, nullable=False)
	formula_id = db.Column(db.Integer, index=True, nullable=False)
	is_owner = db.Column(db.Boolean, server_default='f')
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, user_id, formula_id, is_owner=False):
		self.user_id = user_id
		self.formula_id = formula_id
		self.is_owner = is_owner
	
	def __repr__(self):
		return '<UserFormula(id={}, user_id={}, formula_id={}, is_owner={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.user_id,
			self.formula_id,
			self.is_owner,
			self.created_at,
			self.is_destroyed
		)
