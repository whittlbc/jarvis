from jarvis.helpers import db
import authed_instances


class Wrapper(object):
	
	def __init__(self, service):
		self.service = db.service(service)
		
		csu = db.current_service_user(service)
		
		instance = getattr(authed_instances, service)(csu['configs'] or {})
		
		for attr in [k for k in instance.__dict__.keys() if not k.startswith('__')]:
			setattr(self, attr, getattr(instance, attr))