from jarvis.core.responder import respond
from jarvis.api.reddit import Reddit
import jarvis.helpers.user as user_helper
import re


def fun_fact(outreach=False, sid=None, with_audio=False):
	# Get an authed Reddit instance.
	reddit = Reddit()
	
	# Get a TIL post this user hasn't seen before.
	post = reddit.unique_post(subreddit='todayilearned')
	
	# Get the post's title
	text = post.title.strip()
	
	# If fun fact is being called from by Jarvis' outreach job, format it appropriately.
	if outreach:
		text = re.sub('^til', '', text, flags=re.I).strip()
		
		user_first_name = user_helper.name().split()[0]
		
		text = 'Hey {}, I just learned {}'.format(user_first_name, text)
	else:
		text = re.sub('^(til that|til of|til)', '', text, flags=re.I).strip()
	
		# capitalize the first letter of the first word if not already.
		if not text[0].isupper():
			text = text[0].upper() + text[1:]
	
	# Add a period if no ending punctuation yet.
	if text[-1] not in ['.', '!']:
		text += '.'
		
	respond(text, with_audio=with_audio, room=sid)