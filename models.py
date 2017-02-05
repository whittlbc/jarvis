import datetime
from jarvis import db, request_helper
from slugify import slugify


class User(db.Model):
	__tablename__ = 'user'
	
	id = db.Column(db.Integer, primary_key=True)
	uid = db.Column(db.String, default=request_helper.gen_session_token)
	email = db.Column(db.String)
	password = db.Column(db.String)
	name = db.Column(db.String)
	botname = db.Column(db.String)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, email=None, password=None, name=None, botname='Jarvis'):
		self.email = email
		self.password = password
		self.name = name
		self.botname = botname
	
	def __repr__(self):
		return '<User(id={}, uid={}, email={}, password={}, name={}, botname={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.uid,
			self.email,
			self.password,
			self.name,
			self.botname,
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


class Integration(db.Model):
	__tablename__ = 'integration'
	
	id = db.Column(db.Integer, primary_key=True)
	uid = db.Column(db.String, default=request_helper.gen_session_token)
	name = db.Column(db.String)
	slug = db.Column(db.String)
	logo = db.Column(db.String)
	url = db.Column(db.String)
	user_specific = db.Column(db.Boolean, server_default='f')
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, name=None, logo=None, url=None):
		self.name = name
		self.slug = slugify(name, separator='_')
		self.logo = logo
		self.url = url
	
	def __repr__(self):
		return '<Integration(id={}, uid={}, name={}, slug={}, logo={}, url={}, user_specific={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.uid,
			self.name,
			self.slug,
			self.logo,
			self.url,
			self.user_specific,
			self.created_at,
			self.is_destroyed
		)
		

class UserIntegration(db.Model):
	__tablename__ = 'user_integration'
	
	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, index=True, nullable=False)
	integration_id = db.Column(db.Integer, index=True, nullable=False)
	access_token = db.Column(db.String)
	created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	is_destroyed = db.Column(db.Boolean, server_default='f')
	
	def __init__(self, user_id, integration_id, access_token=None):
		self.user_id = user_id
		self.integration_id = integration_id
		self.access_token = access_token
	
	def __repr__(self):
		return '<UserIntegration(id={}, user_id={}, integration_id={}, access_token={}, created_at={}, is_destroyed={})>'.format(
			self.id,
			self.user_id,
			self.integration_id,
			self.access_token,
			self.created_at,
			self.is_destroyed
		)
