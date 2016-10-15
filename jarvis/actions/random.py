from jarvis.core.responder import respond


def yeezy(e):
	respond(
		'Yeezy taught me.',
		with_audio=True,
		data={
			'soundbite': 'http://confluxapp.s3-website-us-west-1.amazonaws.com/files/ytm.m4a'
		}
	)