from jarvis.api.abstract_api import AbstractApi
import os


class Uber(AbstractApi):
	slug = os.path.basename(__file__)[:-3]
	
	def __init__(self):
		AbstractApi.__init__(self, self.slug)
	
	def request_ride(self):
		return ''