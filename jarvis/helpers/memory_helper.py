import jarvis.helpers.nlp.stanford_parser as sp
from jarvis.helpers.nlp.memory_formats import PREDICATE_FORMATS, RESTRICTED_LABELS
from jarvis.helpers.nlp.lemmatizer import lemmatizer
from jarvis.helpers.nlp.names import names_map
from nltk.tree import Tree
from jarvis import logger

# Configured instance of the Stanford Parser
parser = sp.parser()

words = sp.words
phrases = sp.phrases
clauses = sp.clauses
nouns = sp.nouns
adjectives = sp.adjectives
adverbs = sp.adverbs
verbs = sp.verbs


def format_memory(text):
	tree = to_tree(text)
	
	validations = [
		valid_top_level_structure,
		valid_labels
	]
	
	for v in validations:
		if not v(tree): return None, None

	subj_tree, pred_tree = tree[0][0], tree[0][1]
	
	chopped_subject = chop_np(subj_tree)
	
	if not chopped_subject:
		return None, None
	
	format, pred_content = get_predicate_format(pred_tree)
	
	if format not in PREDICATE_FORMATS:
		return None, None
	
	leading_v = pred_content[0]
	modeled_content = format_modeled_content(pred_content[1:])
	
	# pred_handler = {
	# 	'V(BE)': handle_be,
	# 	'V(OWN)': handle_own,
	# 	'V*': handle_action
	# 	# ignore MD starter for now...won't have to do this if we strip those anyways.
	# }[format[0]]
	
	# info = pred_handler(pred_content)
	
	
	# if predicate has a noun phrase in it, we're dealing with some sort of relationship
	# if format_has_label(format, phrases.NOUN_PHRASE):
		# Figure out what type of relationship
		# print
	
	# Do what you need to with chopped_subject
	# both choppped_subject['noun'] and chopped_subject['owner'] are subjects (2 upsertions)
	# if chopped_subject['owner'] exists, then you know you have a relationship of S_POSS_S to upsert
	# if either choppped_subject['description']['adj'] or choppped_subject['description']['adv'] have contents, then you
	# know you'll need to upsert a description (if no possesssion, upsert a SubjectDescription for noun; if possession,
	# upsert a RelationshipDescription where 'component' is noun)
	
	
	# Need to send back info about what was saved so that Jarvis can reiterate that to the user
	return chopped_subject, format


# [
# 	[{'V*': 'playing'}, {'NP': {'owner': None, 'noun': 'basketball', 'description': {'adv': [], 'adj': []}}}]
# ]
def format_modeled_content(data):
	modeled_data = []
	content = {}
		
	for child in data:
		if isinstance(child, list):
			modeled_data.extend([format_modeled_content(child)])
			return modeled_data
		else:
			key = child.keys()[0]
			val = child[key]
			
			if key == 'V*':
				content['action'] = {
					'v': val,
					'adj': [],
					'adv': [],
					'subject': None
				}
				
			elif key == 'NP':
				if content.get('action'):
					content['action']['subject'] = val
				else:
					content['subject'] = val
			
	modeled_data.append(content)
			
	return modeled_data


def handle_be(pred_content):
	content = []
	
	for child in pred_content[1:]:
		label = child.keys()[0]
		
		data = {}
		
		if label == phrases.VERB_PHRASE:
			content.extend([handle_be(child[label])])
		
		elif label == phrases.NOUN_PHRASE:
			data['noun'] = chop_np(child[label])
			content.append(data)
			
		elif label == phrases.PREP_PHRASE:
			data['pp'] = chop_pp(child[label])
			content.append(data)
		
		elif label in verbs:
			data['action'] = child[label]
			content.append(data)
		
	return content


def handle_own(pred_content):
	# NP exists. You know this already
	print


def handle_action(pred_content):
	print
	

def format_has_label(format, label, final_return=True):
	bools = []
	
	for c in format:
		if isinstance(c, dict):
			bools.extend(format_has_label(c[c.keys()[0]], label, final_return=False))
		else:
			bools.append(c == label)

	if final_return:
		return True in bools
	else:
		return bools


def valid_top_level_structure(t):
	return t[0].label() == clauses.DECLARATION \
		and len(t[0]) == 2 \
		and t[0][0].label() == phrases.NOUN_PHRASE \
		and t[0][1].label() == phrases.VERB_PHRASE


def valid_labels(tree):
	for label in [l[0] for l in labeled_leaves(tree)]:
		if label in RESTRICTED_LABELS:
			return False
	
	return True


def labeled_leaves(tree):
	leaves = []
	
	for child in tree:
		if is_tree(child):
			leaves.extend(labeled_leaves(child))
		else:
			leaves.append([tree.label(), child])
	
	return leaves


# Need to format a response into some when/where/with style structure
def chop_pp(pp):
	return {}


def chop_np(np):
	if not valid_np_children(np):
		return None
	
	subject = {'noun': None, 'owner': None}
	adjs, advs = [], []
		
	groups = labeled_leaves(np)
	
	i = 0
	for g in groups:
		label, word = g
		
		if not subject['noun'] and label in nouns:
			subject['noun'] = word
		elif label in adjectives:
			adjs.append(word)
		elif label in adverbs:
			advs.append(word)
		
		if label == words.POSSESSIVE_PRONOUN:
			subject['owner'] = word
			subject['noun'] = None
		elif label == words.POSSESSIVE_ENDING and i > 0:
			subject['owner'] = groups[i - 1][1]
			subject['noun'] = None
			
		i += 1
	
	if not subject['noun']:
		return None
	
	data = {
		'noun': subject['noun'],
		'owner': None,
		'description': {
			'adj': adjs,
			'adv': advs
		}
	}
	
	# if possession exists
	if subject['owner']:
		data['owner'] = corrected_owner(subject['owner'])
		
	return data


def corrected_owner(owner):
	if owner.lower() in ['my', 'our']:
		return 'I'
	else:
		return owner
	
	
def get_predicate_format(tree):
	format = []
	format_content = []
	
	for child in tree:
		if is_tree(child):
			label = child.label()
			
			if label in [phrases.ADJ_PHRASE, phrases.ADV_PHRASE]:
				pass
			
			elif label in [clauses.DECLARATION, phrases.VERB_PHRASE]:
				f = {}
				f[label], fc = get_predicate_format(child)
				
				format.extend([f])
				format_content.extend([fc])
				
			elif label in [phrases.NOUN_PHRASE, phrases.PREP_PHRASE]:
				pp_children = [c for c in child if has_label(c, phrases.PREP_PHRASE)]
				
				if pp_children:
					error('{} tree cannot have and PP\'s for children just yet'.format(label))
				
				format.append(label)
				
				content = {}
				
				if label == phrases.NOUN_PHRASE:
					content[label] = chop_np(child)
				else:
					content[label] = chop_pp(child)
				
				format_content.append(content)
				
			elif label in verbs:
				corrected_verb_tag = get_verb_tag(child[0])
				format.append(corrected_verb_tag)
				content = {}
				content[corrected_verb_tag] = child[0]
				format_content.append(content)
				
			elif label in [words.MODAL, words.TO]:
				format.append(label)
				content = {}
				content[label] = child[0]
				format_content.append(content)
				
			else:
				error('Invalid tree label while parsing predicate: {}'.format(label))

	return format, format_content
				

def get_verb_tag(verb):
	lemmatized_verb = lemmatize(verb.lower(), pos='v')
	
	if lemmatized_verb == 'be' and verb.lower() not in ['be', 'being']:
		return 'V(BE)'
	elif lemmatized_verb in ['have', 'own', 'possess']:
		return 'V(OWN)'
	else:
		return 'V*'

def valid_np_children(np):
	valid_child_labels = set([
		phrases.NOUN_PHRASE,
		phrases.ADJ_PHRASE,
		phrases.ADV_PHRASE,
		words.NUMBER,
		words.DETERMINER,
		words.ADJ,
		words.ADJ_COMPARATIVE,
		words.ADJ_SUPERLATIVE,
		words.NOUN_SINGULAR,
		words.NOUN_PLURAL,
		words.PROPER_NOUN_SINGULAR,
		words.PROPER_NOUN_PLURAL,
		words.PREDETERMINER,
		words.POSSESSIVE_ENDING,
		words.PERSONAL_PRONOUN,
		words.POSSESSIVE_PRONOUN,
		words.ADV,
		words.ADV_COMPARATIVE,
		words.ADV_SUPERLATIVE,
		words.SYMBOL,
	])

	for l in all_nested_labels(np):
		if l not in valid_child_labels:
			return False
		
	return True
	

def all_nested_labels(tree):
	labels = []
	
	for child in tree:
		if is_tree(child):
			labels.append(child.label())
			labels.extend(all_nested_labels(child))
	
	return labels


def to_tree(text):
	return list(parser.raw_parse(text))[0]


def children_with_label(tree, label):
	return [child for child in tree if is_tree(child) and child.label() == label]


def has_label(t, label):
	return is_tree(t) and t.label() == label


def is_tree(t):
	return isinstance(t, Tree)


def lemmatize(w, pos='n'):
	return lemmatizer.lemmatize(w, pos=pos)


def is_name(name):
	return bool(names_map.get(name))


def assert_label(tree, label):
	if not is_tree(tree):
		error('Label Assertion Error: Tree isn\'t even a tree: {}'.format(tree))
		
	if tree.label() != label:
		error('Label Assertion Error: Label was {}; Expected {}.'.format(tree.label(), label))

		
def error(msg=''):
	raise BaseException(msg)