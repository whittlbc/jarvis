from jarvis import db, logger


IS_DESTROYED = 'is_destroyed'


def find(model, params=None, session=None, unscoped=False):
	params, session = ensure_args(params, session)
	
	if hasattr(model, IS_DESTROYED) and not params.get(IS_DESTROYED) and not unscoped:
		params[IS_DESTROYED] = False
	
	return session.query(model).filter_by(**params).first()


def where(model, params=None, session=None, unscoped=False):
	params, session = ensure_args(params, session)
	exact_params = {}
	list_params = {}
	
	for k, v in params.iteritems():
		if type(v).__name__ in ['list', 'tuple']:
			list_params[k] = tuple(v)
		else:
			exact_params[k] = v
			
	if hasattr(model, IS_DESTROYED) and not exact_params.get(IS_DESTROYED) and not unscoped:
		exact_params[IS_DESTROYED] = False
		
	query = session.query(model).filter_by(**exact_params)
	
	for k, v in list_params.iteritems():
		query = query.filter(getattr(model, k).in_(v))
		
	return query.all()


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
	except Exception as e:
		raise Exception('Error updating {} with params: {} with error: {}'.format(type(model_instance).__name__, params, e.message))
	
	return model_instance


def create(model, params=None, session=None):
	params, session = ensure_args(params, session)
	model_instance = model(**params)
	
	try:
		session.add(model_instance)
		session.commit()
	except Exception as e:
		raise Exception('Error creating {} with params: {} with error: {}'.format(model, params, e.message))
		
	return model_instance
	

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
		raise Exception('Can\'t undestroyed a model ({}) without an \'is_destroyed\' column.'.format(model))
	
	params, session = ensure_args(params, session)
	result = find(model, params, session)
	
	if result:
		try:
			result.is_destroyed = False
			session.commit()
		except Exception as e:
			raise Exception('Error creating {} with params: {} with error: {}'.format(model, params, e.message))
		
		return True
	else:
		return False


def undestroy_instance(model_instance, session=None):
	if not hasattr(model_instance, IS_DESTROYED):
		raise Exception('Can\'t undestroyed a model ({}) without an \'is_destroyed\' column.'.format(type(model_instance).__name__))

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
		except Exception as e:
			raise Exception('Error deleting {} with params: {} with error: {}'.format(model, params, e.message))
		
		return True
	else:
		return False


def delete_instance(model_instance, session=None):
	session = session or create_session()
	
	try:
		session.delete(model_instance)
		session.commit()
	except Exception as e:
		raise Exception('Error deleting {} with error: {}'.format(type(model_instance).__name__, e.message))
	
	return True
	
	
def create_session():
	return db.session


def commit_session(session, quiet=False):
	try:
		session.commit()
		return True
	except Exception as e:
		err_msg = 'Error commiting DB session with error: {}'.format(e.message)
		
		if quiet:
			logger.error(err_msg)
		else:
			raise Exception(err_msg)
		
		return False
			

def ensure_args(params, session):
	params = params or {}
	session = session or create_session()
	return params, session