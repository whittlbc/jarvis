from jarvis.core.responder import respond


def yeezy(m):
	respond(
		'Yeezy taught me.',
		with_audio=True,
		data={
			'soundbite': 'http://confluxapp.s3-website-us-west-1.amazonaws.com/files/ytm.m4a'
		}
	)
	

def airhorn_resp(m):
	respond(
		'You got it.',
		with_audio=True,
		data={
			'soundbite': 'http://confluxapp.s3-website-us-west-1.amazonaws.com/jarvis/airhorn.mp3'
		}
	)
	

def echo_resp(m):
	respond(m.text[5:])
