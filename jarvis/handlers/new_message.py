from jarvis.core import CoreEvent
from jarvis import jarvis
import re


# Look for matches amongst any of the registered formula's regex patterns.
# Perform formula callback if there's a match.
# Do nothing if no match.
def perform(event):
	text = event['text']
	matches_map = {}
		
	# for all the regex patterns registered to jarvis
	for pattern in jarvis.formulas.keys():
		info = jarvis.formulas[pattern]
		flags = 0
		
		# convert string regex flags into python regex flags
		for char in list(info['flags'] or ''):
			flags += getattr(re, char.upper())
		
		matches_map[pattern] = re.findall(pattern, text, flags)

	most_matched_pattern = max(matches_map, key = lambda x: len(set(matches_map[x])))
	matches = matches_map[most_matched_pattern]
	
	# If there's a match, call the registered callback for the matching formula.
	if matches:
		cb = jarvis.formulas[most_matched_pattern]['cb']
		
		core_event = CoreEvent(
			event['type'],
			text,
			most_matched_pattern,
			matches
		)
		
		cb(core_event)
