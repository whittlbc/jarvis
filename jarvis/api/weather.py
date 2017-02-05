from wrapper import Wrapper


class Weather(Wrapper):
	
	def __init__(self, user):
		Wrapper.__init__(self, __name__.split('.').pop(), user)