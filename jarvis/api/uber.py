from jarvis.api.abstract_api import AbstractApi
import os


class Uber(AbstractApi):
	slug = os.path.basename(__file__)[:-3]
	
	def __init__(self):
		# Using this until I can figure out the proper way to call __init__ with super
		self.post_init(self.slug)
	
	def request_ride(self):
		return ''