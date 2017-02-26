from db_helper import find
from models import Integration, UserIntegration
import authed_instances
import inspect


class Wrapper(object):

	def __init__(self, slug, user):
		self.user = user
		self.integration = find(Integration, {'slug': slug})
		self.user_integration = None
		
		if not self.integration:
			raise BaseException('No integration for slug, {}'.format(slug))
		
		configs = {}
		
		# If integration is user-specific, get the UserIntegration record so that
		# we can get the proper configs for creating an authed instance for this integration.
		if self.integration.user_specific:
			self.user_integration = find(UserIntegration, {
				'user_id': self.user.id,
				'integration_id': self.integration.id
			})
			
			configs = {
				'access_token': self.user_integration.access_token,
				'refresh_token': self.user_integration.refresh_token,
				'metadata': self.user_integration.meta
			}
			
		authed_instance = getattr(authed_instances, slug)(**configs)

		# attach all methods from the authed instance (using 3rd-party api library) to this class
		for attr_tup in [t for t in inspect.getmembers(authed_instance) if not t[0].startswith('__')]:
			setattr(self, attr_tup[0], attr_tup[1])