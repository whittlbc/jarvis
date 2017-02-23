from jarvis.helpers.configs import config

 
# def reddit(configs):
# 	import praw
#
# 	return praw.Reddit(
# 		user_agent=configs['REDDIT_USER_AGENT'],
# 		client_id=configs['REDDIT_CLIENT_ID'],
# 		client_secret=configs['REDDIT_CLIENT_SECRET']
# 	)
#
#
# def google(configs):
# 	from googleapiclient.discovery import build
# 	return build('customsearch', 'v1', developerKey=configs['GOOGLE_API_KEY']).cse()

def weather():
	import pyowm
	return pyowm.OWM(config('OWM_API_KEY'))


def uber(access_token=None):
	# TODO: This.
	import uber_rides
	return


def places():
	from googleplaces import GooglePlaces
	return GooglePlaces(config('GOOGLE_API_KEY'))