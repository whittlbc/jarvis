from jarvis.core.responder import respond
import jarvis.helpers.user as user_helper
import re


def name(m):
	# First let's figure out whether the user is requesting his/her name or the bot's name:
	
	# If the query has a possessive pronoun, assume that's the person whose name we want: your name vs. my name.
	if m.has_pos('PRP$'):
		pprp = m.first_of_tag('PRP$')
		is_jarvis = pprp in m.sp_poss_prons
	else:
		prp = m.first_of_tag_after_tag('PRP', 'VB')
		
		# if no PRP after a VB, get the first PRP in the query
		if not prp:
			prp = m.first_of_tag('PRP')
		
		is_jarvis = prp and prp in m.sp_prons
	
	full_name = user_helper.name(is_jarvis=is_jarvis)
	
	# Now let's figure out whether to respond with first name, last name, or full name:
	fn = 'first name'
	ln = 'last name'
	
	# Check to make sure they didn't ask for just their first or last name:
	matches = set(re.compile('{}|{}'.format(fn, ln)).findall(m.clean_text))
	
	wants_fn = fn in matches
	wants_ln = ln in matches
	
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
				resp = 'I don\'t have a last name :('
	
	if m.has_pos('WP', 'who'):
		if is_jarvis:
			prefix = "I'm"
		else:
			prefix = "You're"
			
		resp = "{} {}.".format(prefix, resp)
	
	respond(resp)