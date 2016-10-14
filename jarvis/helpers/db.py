from configs import configs
from pymongo import MongoClient

client = MongoClient(configs.MONGODB_URI)
db = client[configs.MONGODB_NAME]


def find_one(collection, query):
	return db[collection].find_one(query)


def current_user():
	return find_one('users', {'email': configs.USER_EMAIL})


def service(slug):
	return find_one('services', {'slug': slug})