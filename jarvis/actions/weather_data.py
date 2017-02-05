from abstract_action import AbstractAction
from jarvis.api.weather import Weather
from jarvis.helpers.weather_helper import k2f
from jarvis import logger


class WeatherData(AbstractAction):
	
	def __init__(self, params, user, with_voice=False):
		AbstractAction.__init__(self, params, user, with_voice=with_voice)
		self.api = Weather(self.user)
		print "INITIALIZING SHIT"
	
	def search(self):
		print "SEARCHING WITH PARAMS: {}".format(self.params)
		if self.params.get('current_time') == 'true':
			return self.current()
		else:
			return None
				
	def current(self):
		current_loc = 'Palo Alto,us'
		
		try:
			weather = self.api.weather_at_place(current_loc).get_weather()
			if not weather: return None
			
			temp = weather.get_temperature()
			if not temp: return None
			
			temp = k2f(temp['temp'])
			return self.respond("It's currently {} degrees outside.".format(temp))
		except Exception as e:
			logger.error('Error trying to get current weather data for {}, with error: {}'.format(current_loc, e.message))
		
		return None