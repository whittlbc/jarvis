from jarvis.actions.weather import Weather
from jarvis.actions.uber import Uber


action_map = {
	'weather.search': (Weather, 'search'),
	'uber.request': (Uber, 'request_ride'),
	'uber.specify_destination': (Uber, 'specify_destination'),
	'uber.confirm_request': (Uber, 'confirm_ride_request')
}


def klass_method_for_action(action=''):
	return action_map.get(action)