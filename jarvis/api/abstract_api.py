from jarvis import app
import requests

class AbstractApi():
	
	
	def __init__(self, service):
		# from api info, use configs for this service, headers for this service, and base_url for this service
		return None
	
	
	def get(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		response = requests.get(self.url(route), params = payload or {}, headers = headers or {})
		return self.handle_response(response, err_message)
	
	
	def post(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		response = requests.post(self.url(route), data = payload or {}, headers = headers or {})
		return self.handle_response(response, err_message)
	
	
	def put(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		response = requests.put(self.url(route), data = payload or {}, headers = headers or {})
		return self.handle_response(response, err_message)
	
	
	def delete(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		response = requests.delete(self.url(route), params = payload or {}, headers = headers or {})
		return self.handle_response(response, err_message)

	
	def url(self, route):
		return self.base_url + route
	
	
	def handle_response(self, response, err_message):
		if response.status_code == requests.codes.ok:
			return response.json()
		else:
			raise response.status_code + err_message