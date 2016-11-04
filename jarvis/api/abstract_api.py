import requests
from jarvis.helpers import db


class AbstractApi(object):
	
	def __init__(self, service_slug):
		self.service = db.service(service_slug)
		self.headers = self.service['headers']
		self.configs = self.service['configs']
		self.api_url = self.service['apiUrl']
		
	def get(self, route, **kwargs):
		return self._make_request('get', route, **kwargs)
	
	def post(self, route, **kwargs):
		return self._make_request('post', route, **kwargs)
	
	def put(self, route, **kwargs):
		return self._make_request('put', route, **kwargs)
	
	def delete(self, route, **kwargs):
		return self._make_request('delete', route, **kwargs)
	
	def _make_request(self, method, route, payload=None, add_headers=False, err_message='Jarvis - API Error'):
		# Format and add our headers based on which service this is for
		headers = self._format_headers(add_headers)
		
		# Get the proper method (get, post, put, or delete)
		request = getattr(requests, method)

		# Prep the args
		args = {'headers': headers}
		
		if method in ['get', 'delete']:
			args['params'] = payload or {}
		else:
			args['data'] = payload or {}
			
		# Make the request
		response = request(self.api_url + route, **args)
		
		# Return the JSON response
		return self._handle_response(response, err_message)

	def _format_headers(self, add_headers):
		if add_headers:
			# format a dict from the current service_user's config/header info that matches
			# up with this service's headers (self.headers)
			return {}
		else:
			return {}
	
	@staticmethod
	def _handle_response(response, err_message):
		if response.status_code == requests.codes.ok:
			return response.json()
		else:
			raise response.status_code + err_message
