from jarvis.api.wrapper import Wrapper


class Google(Wrapper):
	
	def __init__(self):
		self.slug = __name__.split('.').pop()
		Wrapper.__init__(self, self.slug)
		
	def search(self, query=None):
		if query is None: return None
		
		custom_search_engine_id = self.configs['GOOGLE_CUSTOM_SEARCH_ENGINE_ID']
		
		if not custom_search_engine_id:
			raise 'Custom Search API not enabled. To access this feature, please go ' \
						'to https://cse.google.com and create a new custom search engine.'
		
		return self.list(q=query, cx=custom_search_engine_id).execute()['items']

	def top_result(self, query=None):
		return self.search(query)[0]