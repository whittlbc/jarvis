from abstract_action import AbstractAction
from jarvis.api.uber import UberApi
from jarvis.actions.places import Places
import db_helper as db
from models import PendingRide
from jarvis import logger
from jarvis.helpers.pending_ride_helper import RideStatus


class Uber(AbstractAction):
	
	def __init__(self, **kwargs):
		AbstractAction.__init__(self, **kwargs)
		self.api = UberApi(self.user)
		self.places = Places()  # Google Places API
	
	def request_ride(self, start_coord=None, end_coord=None):
		# Departure Coordinates
		start_coord = start_coord or self.user_metadata.get('location', {}).get('coordinates')
		
		if not start_coord:
			logger.error('Start coordinates required to request a ride: {}'.format(start_coord))
			return None
		
		# Uber Product ID
		product_id = self.product_id_for_user_loc(start_coord)
		
		if not product_id:
			logger.error('Currently no products available for user location: {}'.format(start_coord))
			return None
		
		# Create a new pending_ride record for this request
		try:
			pending_ride = db.create(PendingRide, {
				'user_integration_id': self.api.user_integration.id,
				'start_coord': start_coord,
				'meta': {'product_id': product_id}
			})
		except Exception as e:
			logger.error('Error creating pending_ride with error: {}'.format(e.message))
			return None
		
		# Destination Location (thanks Google Places API)
		end_location = self.determine_end_loc(start_coord)
		
		if end_location:
			end_coord = end_location.geo_location
		
		if end_coord:
			# Confirm the ride since all required info was provided
			return self.prep_ride_confirmation(pending_ride, end_coord, end_location)
		
		# Ask user for destination since not specified
		return self.respond('Where would you like to go?', post_response_prompt={
			'action': 'uber.specify_destination',
			'resource_uid': pending_ride.uid
		})
			
	def specify_destination(self):
		pending_ride = self.find_requested_pending_ride()
		
		if not pending_ride:
			logger.error('No PendingRide for uid: {}'.format(self.params.get('resource_uid')))
			return None

		end_loc_string = self.stored_addr_for_place(self.query) or self.query
		end_location = self.places.first_detailed_nearby(keyword=end_loc_string, lat_lng=pending_ride.start_coord)

		if not end_location:
			logger.error('No end location found for string: {}'.format(end_loc_string))
			return self.respond("I can't find that location for some reason...")
		
		end_coord = end_location.geo_location
		
		if end_coord:
			return self.prep_ride_confirmation(pending_ride, end_coord, end_location)

	def prep_ride_confirmation(self, pending_ride, end_coord, end_location):
		# Convert these from Decimal to float so that they can be JSON serializable
		end_coord['lat'] = float(end_coord['lat'])
		end_coord['lng'] = float(end_coord['lng'])
		
		updated_attrs = {'end_coord': end_coord}
		product_id = pending_ride.meta['product_id']
		start_coord = pending_ride.start_coord
		
		# Get estimated price of ride
		fare = self.get_fare_estimate(product_id, start_coord, end_coord)
		
		if not fare:
			db.update(pending_ride, updated_attrs)  # Still save end_coord for pending_ride
			logger.error('Fare for product_id {} at location {} came back blank...'.format(product_id, start_coord))
			return None
		
		print "GOT FARE: {}".format(fare)
		
		updated_attrs['fare'] = {
			'id': fare['fare_id'],
			'price': fare['value']
		}
			
		db.update(pending_ride, updated_attrs)
		
		# Use specific location components to confirm with the user that he/she wishes to order an Uber to that location
		street_num = street = city = ''
		for comp in end_location.details['address_components']:
			types = comp['types']
			
			if 'street_number' in types:
				street_num = comp['short_name']
			elif 'route' in types:
				street = comp['short_name']
			elif 'locality' in types:
				city = comp['short_name']
			
			if street_num and street and city:
				break
		
		addr_to_confirm = '{} {}'.format(street_num, street)
		
		if city:
			addr_to_confirm += ' in {}'.format(city)
		
		confirmation_msg = 'Are you sure you want an Uber to {} for ${}?'.format(addr_to_confirm, fare['value'])
		
		return self.respond(confirmation_msg, post_response_prompt={
			'action': 'uber.confirm_request',
			'resource_uid': pending_ride.uid
		})

	def confirm_ride_request(self):
		pr = self.find_requested_pending_ride()
		
		if not pr:
			logger.error('No PendingRide for uid: {}'.format(self.params.get('resource_uid')))
			return None
		
		required_info = {
			'product_id': (pr.meta or {}).get('product_id'),
			'start_coord': pr.start_coord,
			'end_coord': pr.end_coord,
			'fare_id': pr.fare['id']
		}
		
		[logger.error("Can't request Uber...{} needs to be present".format(k)) for k, v in required_info.iteritems() if not v]
		
		print 'Requesting Uber from {} to {} for ${}'.format(required_info['start_coord'], required_info['end_coord'], pr.fare['price'])
		
		post_response_prompt = None
		
		if self.is_confirming():
			response = 'Great. Ordering it now.'
		
			resp = self.api.request_ride(
				product_id=required_info['product_id'],
				start_latitude=required_info['start_coord']['lat'],
				start_longitude=required_info['start_coord']['lng'],
				end_latitude=required_info['end_coord']['lat'],
				end_longitude=required_info['end_coord']['lng'],
				seat_count=1,
				fare_id=required_info['fare_id']
			)
	
			# Add ride_id to pending_ride record
			db.update(pr, {'external_ride_id': resp.json.get('request_id')})
			print 'Successfully requested Uber.'
		
		elif self.is_declining():
			response = 'Okay. I\'ll scratch that.'
			db.destroy_instance(pr)
		
		else:
			response = 'I\'m not sure I understand...do you still want me to order that Uber?'
			post_response_prompt = {
				'action': 'uber.confirm_request',
				'resource_uid': pr.uid
			}
		
		return self.respond(response, post_response_prompt=post_response_prompt)
	
	# Used to find pending_ride for param['resource_uid'] provided by client
	def find_requested_pending_ride(self, pending_ride_uid=None):
		pending_ride_uid = pending_ride_uid or self.params.get('resource_uid')
		
		if not pending_ride_uid:
			logger.error('Must provide pending_ride uid when specifying destination for ride')
			return None
		
		return db.find(PendingRide, {'uid': pending_ride_uid, 'status': RideStatus.REQUESTED})
	
	def get_fare_estimate(self, product_id=None, start_coord=None, end_coord=None):
		if not product_id:
			logger.error('Fetching fare estimate requires a product_id...')
			return None
		
		# Get upfront fare for product with start/end location
		estimate = self.api.estimate_ride(
			product_id=product_id,
			start_latitude=start_coord['lat'],
			start_longitude=start_coord['lng'],
			end_latitude=end_coord['lat'],
			end_longitude=end_coord['lng'],
			seat_count=1
		)
		
		if not estimate: return None
		return estimate.json.get('fare')

	def product_id_for_user_loc(self, coordinates):
		products_resp = self.api.get_products(coordinates['lat'], coordinates['lng'])
		products = products_resp.json.get('products')

		if not products: return None
		return products[0].get('product_id')

	def determine_end_loc(self, start_coord):
		str_loc = ''
		address = self.params.get('address')
		city = self.params.get('geo-city')
		place = self.params.get('physical-place')
		given_name = self.params.get('given-name')
		poss_given_name = None
		
		# Figure out if given name possesses the place specified: Ex: "Tyler's house"
		if given_name and place:
			poss = False
			
			for ending in ["'s", "s'", "'"]:
				if (given_name + ending) in self.query:
					poss = True
					poss_given_name = given_name + ending
					break
			
			# if the given name possesses the place...
			if poss and ('{} {}'.format(poss_given_name, place)) in self.query:
				place = '{} {}'.format(poss_given_name, place)
				
				# See if this possessive place is stored in this user's memory
				stored_addr = self.stored_addr_for_place(place)
				
				if stored_addr:
					return self.places.first_detailed_nearby(keyword=stored_addr, lat_lng=start_coord)
				
		if place:
			str_loc += place
		
		if address:
			str_loc += (' ' + address)
		
		if city and city not in (address or ''):
			str_loc += (' ' + city)
			
		if not str_loc:
			return None
		
		return self.places.first_detailed_nearby(keyword=str_loc, lat_lng=start_coord)
	
	def is_confirming(self):
		return self.query.strip().lower() in [
			'yes',
			'yea',
			'yeah',
			'yep',
			'yup',
			'yes I do',
			'yeah I do',
			'yep I do',
			'yup I do',
			'yes I sure do',
			'yeah I sure do',
			'yep I sure do'
			'yup I sure do',
			'I sure do',
			'yes please',
			'You bet your ass I do',
			'please',
			'for sure',
			'lets do it',
			'let\'s do it',
			'absolutely',
			'definitely',
			'oh yeah',
			'uh huh',
			'yeppers',
			'def',
			'defs',
			'most def',
			'most definitely',
			'fa sho',
			'fa shosies',
			'why not',
			'yes let\'s do it',
			'yeah let\'s do it',
			'yea let\'s do it',
			'yup let\'s do it',
			'yep let\'s do it',
			'yes lets do it',
			'yeah lets do it',
			'yea lets do it',
			'yup lets do it',
			'yep lets do it',
			'hells yes',
			'hells yeah',
			'hells yea',
			'hell yes',
			'hell yeah',
			'hell yea',
			'fuck yes',
			'fuck yeah',
			'fuck yea',
			'f yes',
			'f yeah',
			'f yea'
		]
	
	def is_declining(self):
		return self.query.strip().lower() in [
			'no',
			'nope',
			'no thanks',
			'no thank you',
			'never'
			'absolutely not',
			'shut up',
			'go away',
			'nevermind',
			'hell naw',
			'hells naw',
			'hell no',
			'naw',
			'naw bro',
			'fuck off'
		]
	
	@staticmethod
	# TODO: Errrthang for this.
	def stored_addr_for_place(place):
		return None
