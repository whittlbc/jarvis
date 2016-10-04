class AbstractApi():
	
	
	def __init__(self, configs = None):
		self.configs = configs or {}
	
	
	def get(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		payload = payload or {}
		headers = headers or {}
		return self.form_request(net_obj, route, payload, headers, err_message)
	
	
	def post(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		payload = payload or {}
		headers = headers or {}
		return self.json_request(net_obj, route, payload, headers, err_message)
	
	
	def put(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		payload = payload or {}
		headers = headers or {}
		return self.json_request(net_obj, route, payload, headers, err_message)
	
	
	def delete(self, route, payload = None, headers = None, err_message = 'Jarvis - API Error'):
		payload = payload or {}
		headers = headers or {}
		return self.form_request(net_obj, route, payload, headers, err_message)
	
	
	def form_request(self, net_obj, route, payload, headers, err_message):
		if payload:
			route = route + '?' + URI.encode_www_form(payload)
			
		request = net_obj.new(route)
		request.add_field('Content-Type', 'application/x-www-form-urlencoded')
		self.add_headers(request, headers)
		response = self.http().request(request)
		self.handle_json_response(response, err_message)
	
	
	def json_request(self, net_obj, route, payload, headers, err_message):
		request = net_obj.new("/api#{route}")
		request.add_field('Content-Type', 'application/json')
		self.add_headers(request, headers)
		request.body = payload.to_json
		response = self.http().request(request)
		self.handle_json_response(response, err_message)
	
	
	def http(self):
		uri = URI.parse(self.host_url)
		http = Net::HTTP.new(uri.host, uri.port)
		if uri.scheme == 'https':
			http.use_ssl = True
			
		return http
	
	
	def add_headers(self, request, headers):
		for key in headers.keys():
			request.add_field(key, headers[key])
	

	def handle_json_response(self, response, err_message):
		if response.code.to_i == 200:
			# use json decoder
			# JSON.parse(response.body) rescue {}
		else:
			raise err_message