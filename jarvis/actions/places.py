from abstract_action import AbstractAction
from jarvis.api.places import PlacesApi
from jarvis import logger


class Places(AbstractAction):
	MAX_RADIUS = 50000
	
	def __init__(self, **kwargs):
		AbstractAction.__init__(self, **kwargs)
		self.api = PlacesApi(self.user)

	def first_detailed_nearby(self, **kwargs):
		kw = kwargs or {}
		kw['radius'] = kwargs.get('radius') or self.MAX_RADIUS
		
		try:
			result = self.api.nearby_search(**kw)
			if not result or not result.places: return None
			
			place = result.places[0]
			place.get_details()
			return place
		except Exception as e:
			logger.error('Error fetching detailed place, with error: {}'.format(e.message))
			return None