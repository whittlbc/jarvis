from converse import Converse
from weather_data import WeatherData


action_map = {
	'input.greeting': (Converse, 'greet'),
	'input.good_morning': (Converse, 'morning'),
	'weather.search': (WeatherData, 'search')
}

def klass_method_for_action(action=''):
	return action_map.get(action)