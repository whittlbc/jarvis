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


def uber(access_token=None, refresh_token=None, metadata=None):
	from uber_rides.client import UberRidesClient
	from uber_rides.session import OAuth2Credential
	from uber_rides.session import Session
	
	oauth2credential = OAuth2Credential(
		client_id=config('UBER_CLIENT_ID'),
		access_token=access_token,
		expires_in_seconds=metadata.get('expires_in_seconds'),
		scopes=config('UBER_SCOPES'),
		grant_type=metadata.get('grant_type'),
		redirect_url=metadata.get('redirect_url'),
		client_secret=config('UBER_CLIENT_SECRET'),
		refresh_token=refresh_token
	)
	
	session = Session(oauth2credential=oauth2credential)
	return UberRidesClient(session, sandbox_mode=(not config('PRODUCTION')))


def places():
	from googleplaces import GooglePlaces
	return GooglePlaces(config('GOOGLE_API_KEY'))