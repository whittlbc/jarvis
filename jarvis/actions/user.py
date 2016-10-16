from jarvis.core.responder import respond
import jarvis.helpers.user as user_helper
import re


def name(e):
	fn = 'first name'
	ln = 'last name'
	
	print e.text
	
	# Check to make sure they didn't ask for just their first or last name:
	matches = set(re.compile('{}|{}'.format(fn, ln)).findall(e.text))
	
	wants_fn = fn in matches
	wants_ln = ln in matches
	
	# Get the user's full name from the DB
	full_name = user_helper.name()
	
	# If both or none are specified, just return the full name
	if (wants_fn and wants_ln) or (not wants_fn and not wants_ln):
		resp = full_name
	else:
		split_name = full_name.split(' ')
		
		# Requesting first name only
		if wants_fn:
			resp = split_name[0]
		
		# Requesting last name only
		else:
			# Check that they actually have a last name
			if len(split_name) > 1:
				resp = split_name[len(split_name) - 1]
			else:
				resp = 'I don\'t have a last name!'
			
	if 'who ' in e.text.lower():
		resp = "You're {}.".format(resp)
	
	respond(resp, with_audio=False)
