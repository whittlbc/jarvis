import time
import json
import copy
from configs import configs
from pymongo import MongoClient
from jarvis.helpers.cache import cache


client = MongoClient(configs.MONGODB_URI)
db = client[configs.MONGODB_NAME]


def insert(collection, data, remove_from_redis=None):
	db[collection].insert(data)
	
	if remove_from_redis:
		cache.delete(remove_from_redis)


def update(collection, filter, updates, remove_from_redis=None):
	db[collection].update_one(filter, {'$set': updates})
	
	if remove_from_redis:
		cache.delete(remove_from_redis)
		

def remove(collection, filter):
	return db[collection].remove(filter)


def find_one(collection, query):
	return db[collection].find_one(query)


def find(collection, query=None):
	return list(db[collection].find(query or {}))


def messages():
	return db['messages']


def users():
	return db['users']


def current_user():
	return find_one_optimal('current_user', 'users', {'email': configs.USER_EMAIL})


def service(slug):
	return find_one('services', {'slug': slug})


def get_jarvis():
	return find_one_optimal('jarvis', 'users', {'isJarvis': True})


def find_one_optimal(redis_key, mongo_collection, mongo_query):
	record = cache.get(redis_key)
	
	if record:
		return json.loads(record)
	else:
		record = find_one(mongo_collection, mongo_query)
		mod_record = copy.deepcopy(record)
		mod_record['_id'] = str(mod_record['_id'])
		cache.set(redis_key, json.dumps(mod_record))
		return mod_record


def oid(doc):
	return str(doc['_id'])


def save_message(message, from_jarvis=False, correct_me=False, is_command=False):
	data = {
		'text': message['text'],
		'isAudio': message['isAudio'],
		'ts': time.time()
	}
	
	if from_jarvis:
		user = get_jarvis()
		data['correctMe'] = correct_me
	else:
		user = current_user()
		data['isCommand'] = is_command
		
	data['user_oid'] = oid(user)
	
	insert('messages', data)
	

# Get the message cached in redis and write it's data to the correct csv
# as another data point. Add this new message to the cache as a replacement.
def update_msg_cache(text, action):
	lc_key = 'last_command'
	
	# Get the last command info from redis
	lc = cache.get(lc_key)
	
	# Cache the new message info
	cache.set(lc_key, json.dumps({'text': text, 'action': action}))
	
	if lc:
		try:
			lc = json.loads(lc)
			
			if lc['action']:
				import jarvis.learn.classify.train as trainer
				trainer.update_train_data(lc['text'], lc['action'])
		except:
			print 'Error parsing message json from cache'


def update_last_command_action(action):
	lc_key = 'last_command'
	
	# Get the last command info from redis
	lc = cache.get(lc_key)
	
	if lc:
		# parse it into object
		lc = json.loads(lc)
		
		# Update it with the proper action
		cache.set(lc_key, json.dumps({'text': lc['text'], 'action': action}))


def update_memory_attrs(mem_key, new_attrs):
	update('memories', {'key.lower': mem_key.lower()}, {'attrs': new_attrs}, remove_from_redis='memories')


def insert_new_memory(mem_key, attr_type, attr_value):
	new_memory = {
		'key': {
			'orig': mem_key,
			'lower': mem_key.lower()
		},
		'attrs': {
			'who': {
				'orig': '',
				'lower': ''
			},
			'what': {
				'orig': '',
				'lower': ''
			},
			'when': {
				'orig': '',
				'lower': ''
			},
			'where': {
				'orig': '',
				'lower': ''
			}
		},
		'ts': time.time()
	}
	
	attr_value_map = {
		'orig': attr_value,
		'lower': attr_value.lower()
	}
	
	new_memory['attrs'][attr_type] = attr_value_map
	
	if attr_type == 'who':
		new_memory['attrs']['what'] = attr_value_map
	
	insert('memories', new_memory, remove_from_redis='memories')


def update_memory(mem_key, attr_type, attr_value):
	memories = cache.get('memories')
	
	if memories is None:
		# Get memory from DB since 'memories' NOT in redis
		memory = find_one('memories', {'key.lower': mem_key.lower()}) or {}
	else:
		# Get memory from redis
		memory = json.loads(memories).get(mem_key.lower()) or {}
		
	attrs = memory.get('attrs')
	
	if attrs:
		# if attrs already exist, just update the one you need to:
		attrs[attr_type] = {
			'orig': attr_value,
			'lower': attr_value.lower()
		}
		
		update_memory_attrs(mem_key, attrs)
	else:
		# otherwise, create a new memory from scratch
		insert_new_memory(mem_key, attr_type, attr_value)


def get_memory(subject, wh):
	memories = get_memories()
	split_subject = subject.split(' ')
	
	# If dealing with something like "who is (in|at)" or "what is (in|at|on)"...
	# For now, only 'in' and 'at' correlate to 'where', while 'on' correlates to 'when'.
	# I realize that 'on' could also be used as a where preposition, but just gonna deal with that later.
	who_or_what_with_prep = (wh == 'who' and split_subject[0] in ['in', 'at']) or \
		(wh == 'what' and split_subject[0] in ['in', 'at', 'on'])
	
	if who_or_what_with_prep:
		prep = split_subject[0]
		subject = ' '.join(split_subject[1:])
		
		wh_for_prep = {
			'in': 'where',
			'at': 'where',
			'on': 'when'
		}[prep]
		
		keys = []
		for k, v in memories.iteritems():
			if v['attrs'][wh_for_prep]['lower'] == subject:
				keys.append(v['orig'])
	else:
		# At this point, try getting record just by key: <subject>
		memory = memories.get(subject)
		
		# if memory exists for that subject, return the requested attr
		if memory:
			return memory['attrs'][wh]['orig']
		
		# Otherwise, we need to do a "backwards" search -- looking up documents where v['attrs'][X] == subject
		keys = []
		for k, v in memories.iteritems():
			attrs = v['attrs']
			result = None
			
			if wh == 'what':
				if subject in [attrs['what']['lower'], attrs['who']['lower']]:
					result = v['orig']
				
			elif wh == 'where':
				if subject in [attrs['what']['lower'], attrs['who']['lower']]:
					result = attrs[wh]['orig']
					
			elif wh == 'when':
				if subject == attrs['what']['lower']:
					result = attrs[wh]['orig']
				
			else:
				if subject == attrs[wh]['lower']:
					result = v['orig']
			
			if result:
				keys.append(result)
				
		if not keys:
			return None
	
	return comma_delimit(keys)
						

def comma_delimit(keys):
	if len(keys) > 2:
		keys = ', '.join(keys[:-1]) + ', and ' + keys[-1]
	else:
		keys = ' and '.join(keys)
	
	return keys


def get_memories():
	# First try getting memories from redis
	memories = cache.get('memories')
	
	# if the memories key doesn't exist yet in redis, we should get the memory
	# results from mongodb and store them under 'memory' key in redis (even if empty array).
	if memories is None:
		memories = find('memories')
		mem_map = {}
		
		for mem in memories:
			mem_map[mem['key']['lower']] = {
				'orig': mem['key']['orig'],
				'attrs': mem['attrs']
			}
			
		memories = json.dumps(mem_map)
		cache.set('memories', memories)
	
	return json.loads(memories)


def forget_memory(mem_key):
	op = remove('memories', {'key.lower': mem_key})
	had_memory = op['n'] > 0
	
	if had_memory: cache.delete(mem_key)
	
	return had_memory


def current_service_user(service_slug):
	current_user_oid = oid(current_user())
	return find_one('service_users', {'user_oid': current_user_oid, 'service_slug': service_slug})


def content_ids_for_service(service_slug):
	# Try fetching from cache first
	if cache.exists('service_user_content'):
		content_ids = cache.hget('service_user_content', service_slug)
	else:
		# Not in cache, so lets fetch from persistent db and then cache the results.
		# First get the current service user (we'll need his oid)
		csu = current_service_user(service_slug)
			
		# if service_user doesn't exist for this service as the current user, just return None (for now).
		if not csu:
			print 'Current service_user does not exist for service: {}'.format(service_slug)
			return None
		
		# Fetch all service_user_content for this user, grouped by service
		content = find('service_user_content', {'service_user_oid': oid(csu)})
		if not content: return None
		
		content_by_service = {}
		
		for record in content:
			service = record['service_slug']
			
			if not content_by_service.get(service):
				content_by_service[service] = []
				
			content_by_service[service].append(record['content_id'])
			
		for k, v in content_by_service.iteritems():
			cache.hset('service_user_content', k, v)
			
		content_ids = content_by_service[service_slug]
		
	return content_ids


def add_service_user_content(content_id, service_slug):
	csu = current_service_user(service_slug)
	
	# if service_user doesn't exist for this service as the current user, just return None (for now).
	if not csu:
		raise 'Current service_user does not exist for service: {}'.format(service_slug)
	
	data = {
		'service_user_oid': oid(csu),
		'service_slug': service_slug,
		'content_id': content_id
	}
	
	insert('service_user_content', data, remove_from_redis='service_user_content')