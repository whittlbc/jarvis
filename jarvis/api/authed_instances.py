

def reddit(configs):
	import praw
	
	return praw.Reddit(
		user_agent=configs['REDDIT_USER_AGENT'],
		client_id=configs['REDDIT_CLIENT_ID'],
		client_secret=configs['REDDIT_CLIENT_SECRET']
	)