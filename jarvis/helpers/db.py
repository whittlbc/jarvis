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


def find_all(collection):
	return list(db[collection].find())


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
# as another data point. Add this new message to the cache as a replacement
# (only 1 at a time). Then retrain the model.
def update_msg_cache(text, action):
	lc_key = 'last_command'
	
	# Get the last command info from redis
	lc = cache.get(lc_key)
	
	# Cache the new message info
	cache.set(lc_key, json.dumps({'text': text, 'action': action}))
	
	if lc:
		try:
			lc = json.loads(lc)
			
			import jarvis.learn.train as trainer
			trainer.update_train_data(lc['text'], lc['action'])
		except:
			print 'Error parsing message json from cache'


def update_memory_attrs(mem_key, new_attrs):
	update('memories', {'key': mem_key}, {'attrs': new_attrs}, remove_from_redis='memories')


def insert_new_memory(mem_key, attr_type, attr_value):
	new_memory = {
		'key': mem_key,
		'attrs': {
			'who': '',
			'what': '',
			'when': '',
			'where': ''
		},
		'ts': time.time()
	}
	
	new_memory['attrs'][attr_type] = attr_value
	
	if attr_type == 'who':
		new_memory['attrs']['what'] = attr_value
	
	insert('memories', new_memory, remove_from_redis='memories')


def update_memory(mem_key, attr_type, attr_value):
	memories = cache.get('memories')
	
	if memories is None:
		memory = find_one('memories', {'key': mem_key}) or {}
		current_mem_attrs = memory.get('attrs')
	else:
		memories = json.loads(memories)
		current_mem_attrs = memories.get(mem_key)
		
	if current_mem_attrs:
		new_attrs = dict(current_mem_attrs)
		new_attrs[attr_type] = attr_value
		update_memory_attrs(mem_key, new_attrs)
	else:
		insert_new_memory(mem_key, attr_type, attr_value)


def get_memories():
	# First try getting memories from redis
	memories = cache.get('memories')
	
	# if the memories key doesn't exist yet in redis, we should get the memory
	# results from mongodb and store them under 'memory' key in redis (even if empty array).
	if memories is None:
		memories = find_all('memories')
		mem_map = {}
		
		for mem in memories:
			mem_map[mem['key']] = mem['value']
		
		memories = json.dumps(mem_map)
		cache.set('memories', memories)
	
	return json.loads(memories)


def forget_memory(mem_key):
	op = remove('memories', {'key': mem_key})
	had_memory = op['n'] > 0
	
	if had_memory: cache.delete(mem_key)
	
	return had_memory
