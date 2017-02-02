import uuid
import json


class RequestHelper(object):
	
	def __init__(self, app):
		self.app = app
	
	def json_response(self, data=None, status=200, with_cookie=None):
		resp_data = json.dumps(data or {})
		response = self.app.make_response(resp_data)
		
		if with_cookie:
			cookie_name, cookie_val = with_cookie
			response.set_cookie(cookie_name, cookie_val)
		
		return response, status
	
	def error(self, message='', status=400):
		return self.json_response({'error': message}, status=status)

	@staticmethod
	def gen_session_token():
		return uuid.uuid4().hex