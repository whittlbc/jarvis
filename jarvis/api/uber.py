from jarvis.api.abstract_api import AbstractApi

class Uber(AbstractApi):
	
	def __init__(self):
		super(Uber, self).__init__(self, __name__)
	
	def request_ride(self):
		return ''