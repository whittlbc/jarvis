class Response:
	
	def __init__(self, text=None, with_voice=False, soundbite_url=None, attachments=None):
		self.text = text
		self.with_voice = with_voice
		self.soundbite_url = soundbite_url
		self.attachments = attachments
		
	def as_json(self):
		return {
			'text': self.text,
			'withVoice': self.with_voice,
			'soundbiteUrl': self.soundbite_url,
			'attachments': self.attachments
		}