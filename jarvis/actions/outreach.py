from jarvis.core.responder import respond
from jarvis.api.reddit import Reddit


def fun_fact(sid=None):
	til = next(Reddit().subreddit('todayilearned').new(limit=1)).title
	respond(til, room=sid)