from jarvis.core.responder import respond
import jarvis.helpers.user as user_helper
import re


def name(e):
	fn = 'first name'
	ln = 'last name'
	
	# Check to make sure they didn't ask for just their first or last name:
	matches = set(re.compile('{}|{}'.format(fn, ln)).findall(e.text))
	
	wants_fn = fn in matches
	wants_ln = ln in matches
	
	# Get the user's full name from the DB
	full_name = user_helper.name()
	
	# If both or none are specified, just return the full name
	if (wants_fn and wants_ln) or (not wants_fn and not wants_ln):
		name_to_return = full_name
	else:
		split_name = full_name.split(' ')
		
		# Requesting first name only
		if wants_fn:
			name_to_return = split_name[0]
		
		# Requesting last name only
		else:
			# Check that they actually have a last name
			if len(split_name) > 1:
				name_to_return = split_name[len(split_name) - 1]
			else:
				name_to_return = 'I don\'t have a last name!'
			
	respond(name_to_return, with_audio=False)
