from jarvis.core.response import Response


class AbstractAction(object):
	
	def __init__(self, query=None, params=None, user=None, user_metadata=None, with_voice=False):
		self.query = query or ''
		self.params = params or {}
		self.user = user
		self.user_metadata = user_metadata or {}
		self.with_voice = with_voice
		
	def respond(self, text=None, with_voice=None, soundbite_url=None, attachments=None, post_response_prompt=None):
		if with_voice is None:
			with_voice = self.with_voice
		
		return Response(text, with_voice, soundbite_url, attachments, post_response_prompt)