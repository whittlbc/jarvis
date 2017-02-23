from wrapper import Wrapper


class WeatherApi(Wrapper):
	
	def __init__(self, user):
		Wrapper.__init__(self, __name__.split('.').pop(), user)