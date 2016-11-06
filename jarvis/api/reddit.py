from abstract_api import AbstractApi


class Reddit(AbstractApi):
	
	def __init__(self):
		self.slug = __name__.split('.').pop()
		AbstractApi.__init__(self, self.slug, wrapper=True)