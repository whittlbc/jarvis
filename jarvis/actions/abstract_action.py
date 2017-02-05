from jarvis.core.response import Response


class AbstractAction(object):
	
	def __init__(self, params, user, with_voice=False):
		self.params = params or {}
		self.user = user
		self.with_voice = with_voice
		
	def respond(self, text=None, with_voice=None, soundbite_url=None, attachments=None):
		if with_voice is None:
			with_voice = self.with_voice
		
		return Response(text, with_voice, soundbite_url, attachments)