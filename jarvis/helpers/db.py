from jarvis import app
from pymongo import MongoClient

client = MongoClient(app.config.get('MONGODB_URI'))
db = client[app.config.get('MONGODB_NAME')]


def find_one(collection, query):
	return db[collection].find_one(query)


def current_user():
	return find_one('users', { 'email': app.config.get('USER_EMAIL') })