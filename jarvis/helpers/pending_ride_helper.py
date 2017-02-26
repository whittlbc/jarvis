
def uber_status_update(status):
	return {
		'processing': {
			'status': 0,
			'response': None
		},
		'no_drivers_available': {
			'status': 1,
			'response': 'Sorry <USER_NAME>, but no drivers are currently available.',
			'destroy_ride': True
		},
		'accepted': {
			'status': 2,
			'response': 'Hey <USER_NAME>, your ride request has been accepted.'  # add more details later about who/eta
		},
		'arriving': {
			'status': 3,
			'response': 'Hey <USER_NAME>, your Uber driver is arriving now.'
		},
		'in_progress': {
			'status': 4,
			'response': None
		},
		'driver_canceled': {
			'status': 5,
			'response': 'Sorry <USER_NAME>, but your Uber driver had to cancel the trip for some reason.',
			'destroy_ride': True
		},
		'rider_canceled': {
			'status': 6,
			'response': None,
			'destroy_ride': True
		},
		'completed': {
			'status': 7,
			'response': None,
			'destroy_ride': True
		}
	}.get(status)