from jarvis import db, logger

IS_DESTROYED = 'is_destroyed'


def find(model, params=None, session=None, unscoped=False):
	params, session = ensure_args(params, session)
	
	if hasattr(model, IS_DESTROYED) and not params.get(IS_DESTROYED) and not unscoped:
		params[IS_DESTROYED] = False
	
	return session.query(model).filter_by(**params).first()


def where(model, params=None, session=None, unscoped=False):
	params, session = ensure_args(params, session)
	
	if hasattr(model, IS_DESTROYED) and not params.get(IS_DESTROYED) and not unscoped:
		params[IS_DESTROYED] = False
		
	return session.query(model).filter_by(**params).all()


def find_or_initialize_by(model, params=None, session=None, unscoped=False):
	params, session = ensure_args(params, session)
	record = find(model, params, session, unscoped)
	is_new = False
	
	if not record:
		is_new = True
		record = create(model, params, session)
	
	return record, is_new


def update(model_instance, params=None, session=None):
	params, session = ensure_args(params, session)
	
	try:
		[setattr(model_instance, k, v) for k, v in params.iteritems()]
		session.commit()
		return model_instance
	except Exception as e:
		logger.error('Error updating {} with params: {} with error: {}'.format(type(model_instance).__name__, params, e))

	return None
	

def create(model, params=None, session=None):
	params, session = ensure_args(params, session)
	model_instance = model(**params)
	
	try:
		db.session.add(model_instance)
		db.session.commit()
		return model_instance
	except Exception as e:
		logger.error('Error creating {} with params: {} with error: {}'.format(model, params, e))
	
	return None
	

def destroy(model, params=None, session=None):
	if not hasattr(model, IS_DESTROYED):
		return delete(model, params, session)
	
	params, session = ensure_args(params, session)
	result = find(model, params, session)
	
	if result:
		result.is_destroyed = True
		session.commit()
		return True
	
	return False


def destroy_instance(model_instance, session=None):
	if not hasattr(model_instance, IS_DESTROYED):
		return delete_instance(model_instance, session)
	
	session = session or create_session()
	model_instance.is_destroyed = True
	session.commit()
	return True


def undestroy(model, params=None, session=None):
	if not hasattr(model, IS_DESTROYED):
		logger.error('Can\'t undestroyed a model ({}) without an \'is_destroyed\' column.'.format(model))
		return False
	
	params, session = ensure_args(params, session)
	result = find(model, params, session)
	
	if result:
		try:
			result.is_destroyed = False
			session.commit()
			return True
		except Exception as e:
			logger.error('Error creating {} with params: {} with error: {}'.format(model, params, e))
	
	return False


def undestroy_instance(model_instance, session=None):
	if not hasattr(model_instance, IS_DESTROYED):
		logger.error('Can\'t undestroyed a model ({}) without an \'is_destroyed\' column.'.format(type(model_instance).__name__))
		return False

	session = session or create_session()
	model_instance.is_destroyed = False
	session.commit()
	return True


def delete(model, params=None, session=None):
	params, session = ensure_args(params, session)
	result = find(model, params, session)
	
	if result:
		try:
			session.delete(result)
			session.commit()
			return True
		except Exception as e:
			logger.error('Error deleting {} with params: {} with error: {}'.format(model, params, e))
	
	return False


def delete_instance(model_instance, session=None):
	session = session or create_session()
	
	try:
		session.delete(model_instance)
		session.commit()
		return True
	except Exception as e:
		logger.error('Error deleting {} with error: {}'.format(type(model_instance).__name__, e))
	
	return False
	
	
def create_session():
	return db.session

	
def ensure_args(params, session):
	params = params or {}
	session = session or create_session()
	return params, session