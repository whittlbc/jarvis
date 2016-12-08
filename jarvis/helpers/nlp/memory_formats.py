import jarvis.helpers.nlp.stanford_parser as sp
words = sp.words

# Allowed tree formats for predicates when storing memories
STORAGE_PREDICATE_FORMATS = [
	['V(BE)'],
	['V(BE)', 'NP'],
	['V(BE)', 'PP'],
	['V(BE)', 'NP', 'NP'],
	['V(BE)', {'VP': ['V*']}],
	['V(BE)', {'VP': ['V*', 'NP']}],
	['V(BE)', {'VP': ['V*', 'PP']}],
	['V(BE)', {'VP': ['V*', 'NP', 'PP']}],
	['V(BE)', {'VP': ['V*', 'PP', 'NP']}],
	['V(BE)', {'VP': ['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*']}]}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP']}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP', 'NP']}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'PP']}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'PP', 'NP']}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP', 'PP']}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*']}]}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP']}]}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'PP']}]}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'PP', 'NN']}]}]}]}]}],
	['V(BE)', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NN', 'PP']}]}]}]}]}],
	['V(OWN)', 'NP'],
	['V(OWN)', 'NP', 'NP'],
	['V*'],
	['V*', 'NP'],
	['V*', 'PP'],
	['V*', 'NP', 'NP'],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*']}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP']}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP', 'NP']}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'PP']}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'PP', 'NP']}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP', 'PP']}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*']}]}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP']}]}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP', 'NP']}]}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'PP']}]}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'PP', 'NP']}]}]}]}],
	['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP', 'PP']}]}]}]}],
	['MD', {'VP': ['V*']}],
	['MD', {'VP': ['V*', 'NP']}],
	['MD', {'VP': ['V*', 'PP']}],
	['MD', {'VP': ['V*', 'NP', 'PP']}],
	['MD', {'VP': ['V*', 'PP', 'NP']}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*']}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP']}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP', 'NP']}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'PP']}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'PP', 'NP']}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', 'NP', 'PP']}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*']}]}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP']}]}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP', 'NP']}]}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'PP']}]}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'PP', 'NP']}]}]}]}]}],
	['MD', {'VP': ['V*', {'S': [{'VP': ['TO', {'VP': ['V*', {'VP': ['V*', 'NP', 'PP']}]}]}]}]}]
]


# Allowed tree formats for predicates when retrieving a memory with a 'WH' question
WH_RETRIEVAL_PREDICATE_FORMATS = [
	[{'VP': ['V*']}],
	[{'VP': ['V*', 'NP']}],
	['V*', 'NP', {'VP': ['V*']}],
]

# Labels currently restricted when storing memories
RESTRICTED_LABELS = set([
	words.COORD_CONJUNC
])