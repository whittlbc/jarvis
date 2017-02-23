from abstract_action import AbstractAction
from jarvis.api.weather import WeatherApi
from jarvis.helpers.weather_helper import k2f
from jarvis import logger


class Weather(AbstractAction):
	
	def __init__(self, **kwargs):
		AbstractAction.__init__(self, **kwargs)
		self.api = WeatherApi(self.user)
		self.specified_loc = self.specified_date = self.specified_time = False
		self.set_location()
		self.set_date()
		self.set_time()
		
	def set_location(self):
		if self.params.get('location'):
			self.requested_loc = self.params['location']
			self.specified_loc = True
		else:
			user_loc = self.user_metadata.get('location', {})
			self.requested_loc = '{},{}'.format(user_loc.get('city'), user_loc.get('countryCode').lower())
		
	def set_date(self):
		if self.params.get('date'):
			self.requested_date = self.params['date']
			self.specified_date = True
		else:
			self.requested_date = self.user_metadata.get('date')
			
	def set_time(self):
		if self.params.get('time'):
			self.requested_time = self.params['time']
			self.specified_time = True
		else:
			self.requested_time = self.user_metadata.get('time')
			
	def search(self):
		try:
			response = None
			
			print("LOCATION: {}".format(self.requested_loc))
			print("DATE: {}".format(self.requested_date))
			print("TIME: {}".format(self.requested_time))
			
			if self.specified_date or self.specified_time:
				forecaster = self.api.daily_forecast(self.requested_loc)
				datetime = '{} {}:00+00'.format(self.requested_date, self.requested_time)
				weather = forecaster.get_weather_at(datetime)
				
				if weather:
					status = weather.get_detailed_status()
					temp_info = weather.get_temperature()
					response = 'There should be {} with a high of {} and a low of {}.'.format(status, k2f(temp_info['max']), k2f(temp_info['min']))
			else:
				weather = self.api.weather_at_place(self.requested_loc).get_weather()
				
				if weather:
					status = weather.get_detailed_status()
					temp_info = weather.get_temperature()
					response = 'It\'s currently {} degrees with {}.'.format(k2f(temp_info['temp']), status)
				
			if not response:
				return None
			
			return self.respond(response)
		except Exception as e:
			logger.error('Error trying to get current weather data for {}, with error: {}'.format(self.requested_loc, e.message))
		
		return None