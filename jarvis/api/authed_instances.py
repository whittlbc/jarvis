

def reddit(configs):
	import praw
	
	return praw.Reddit(
		user_agent=configs['REDDIT_USER_AGENT'],
		client_id=configs['REDDIT_CLIENT_ID'],
		client_secret=configs['REDDIT_CLIENT_SECRET']
	)


def google(configs):
	from googleapiclient.discovery import build
	return build('customsearch', 'v1', developerKey=configs['GOOGLE_API_KEY']).cse()