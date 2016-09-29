from jarvis.core import CoreEvent
from jarvis import jarvis

def perform(event):
	text = event['text']
	matching_pattern = None
	match = None
	f = None
	
	print jarvis.formulas
	
	for pattern in jarvis.formulas.keys():
		# if match between pattern and text, set matching_pattern and match
		matching_pattern = '/time/'
		match = 'My Match'
		f = jarvis.formulas[pattern]

	core_event = CoreEvent(event['type'], text, matching_pattern, match)
	f(core_event)