import requests
from jarvis.helpers import db


class AbstractApi(object):
	
	
	def __init__(self, service_slug):
		self.service = db.service(service_slug)
		self.configs = self.service['configs']
		self.api_url = self.service['apiUrl']
		self.headers = self.service['headers']
	
	
	def get(self, route, payload = None, add_headers = False, err_message = 'Jarvis - API Error'):
		headers = self.format_headers(add_headers)
		response = requests.get(self.url(route), params = payload or {}, headers = headers)
		return self.handle_response(response, err_message)
	
	
	def post(self, route, payload = None, add_headers = False, err_message = 'Jarvis - API Error'):
		headers = self.format_headers(add_headers)
		response = requests.post(self.url(route), data = payload or {}, headers = headers)
		return self.handle_response(response, err_message)
	
	
	def put(self, route, payload = None, add_headers = False, err_message = 'Jarvis - API Error'):
		headers = self.format_headers(add_headers)
		response = requests.put(self.url(route), data = payload or {}, headers = headers)
		return self.handle_response(response, err_message)
	
	
	def delete(self, route, payload = None, add_headers = False, err_message = 'Jarvis - API Error'):
		headers = self.format_headers(add_headers)
		response = requests.delete(self.url(route), params = payload or {}, headers = headers)
		return self.handle_response(response, err_message)

	
	def format_headers(self, add_headers):
		if add_headers:
			# format a dict from the current service_user's config/header info that matches
			# up with this service's headers (self.headers)
			return {}
		else:
			return {}
	

	def url(self, route):
		return self.api_url + route
	
	
	def handle_response(self, response, err_message):
		if response.status_code == requests.codes.ok:
			return response.json()
		else:
			raise response.status_code + err_message