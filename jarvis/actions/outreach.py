from jarvis.core.responder import respond
from jarvis.api.reddit import Reddit


def fun_fact(sid=None):
	# Get the top TIL post on Reddit
	til = next(Reddit().subreddit('todayilearned').new(limit=1)).title.strip()
	
	# Add a period at the end if not already there.
	if til[-1] not in ['.', '!']:
		til += '.'
		
	# TODO: Parse the title and only keep the words uppercased if they're proper nouns.
	# TODO: Replace TIL with "Hey man, I just learned".
	
	respond(til, room=sid)