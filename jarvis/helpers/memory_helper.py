import jarvis.helpers.nlp.stanford_parser as sp
from jarvis.helpers.nlp.lemmatizer import lemmatizer
from jarvis.helpers.nlp.names import names_map
from nltk.tree import Tree
from jarvis import logger

# Configured instance of the Stanford Parser
parser = sp.parser()
words = sp.words
phrases = sp.phrases
clauses = sp.clauses

# Labels currently restricted
RESTRICTED_LABELS = set([
	words.COORD_CONJUNC
])

# Tree Formats currently allowed
PREDICATE_FORMATS = set([
	'V(BE)',
	'V*',
	'V(BE) + NP(no-pp)',
	'V(OWN) + NP(no-pp)',
	'V* + NP(no-pp)',
	'V(BE) + PP',
	'V* + PP',
	'V(BE) + NP(no-pp) + NP(no-pp)',
	'V(OWN) + NP(no-pp) + NP(no-pp)',
	'V* + NP(no-pp) + NP(no-pp)',
	'V* + S-VP(TO + VP(V*))',
	'V* + S-VP(TO + VP(V* + NP(no-pp)))',
	'V* + S-VP(TO + VP(V* + NP(no-pp) + NP(no-pp)))',
	'V* + S-VP(TO + VP(V* + PP))',
	'V* + S-VP(TO + VP(V* + PP + NP(no-pp)))',
	'V* + S-VP(TO + VP(V* + NP(no-pp) + PP)',
	'V* + S-VP(TO + VP(V* + VP(V*)))',
	'V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp))))',
	'V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp) + NP(no-pp)))',
	'V* + S-VP(TO + VP(V* + VP(V* + PP)))',
	'V* + S-VP(TO + VP(V* + VP(V* + PP + NP(no-pp))))',
	'V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp) + PP)))',
	'V(BE) + VP(V*)',
	'V(BE) + VP(V* + NP(no-pp))',
	'V(BE) + VP(V* + PP)',
	'V(BE) + VP(V* + NP(no-pp) + PP)',
	'V(BE) + VP(V(BE) + VP(V* + S-VP(TO + VP(V*))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + NP(no-pp))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + NP(no-pp) + NP(no-pp))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + PP)))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + PP + NP(no-pp))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + NP(no-pp) + PP))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + VP(V*))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp)))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + VP(V* + PP))))',
	'V(BE) + VP(V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp) + PP))))',
	'MD + VP(V*)',
	'MD + VP(V* + NP(no-pp))',
	'MD + VP(V* + PP)',
	'MD + VP(V* + NP(no-pp) + PP)',
	'MD + VP(V* + S-VP(TO + VP(VB*)))',
	'MD + VP(V* + S-VP(TO + VP(V* + NP(no-pp))))',
	'MD + VP(V* + S-VP(TO + VP(V* + NP(no-pp) + NP(no-pp))))',
	'MD + VP(V* + S-VP(TO + VP(V* + PP)))',
	'MD + VP(V* + S-VP(TO + VP(V* + PP + NP(no-pp))))',
	'MD + VP(V* + S-VP(TO + VP(V* + NP(no-pp) + PP)))',
	'MD + VP(V* + S-VP(TO + VP(V* + VP(V*))))',
	'MD + VP(V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp)))))',
	'MD + VP(V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp) + NP(no-pp))))',
	'MD + VP(V* + S-VP(TO + VP(V* + VP(V* + PP))))',
	'MD + VP(V* + S-VP(TO + VP(V* + VP(V* + PP + NP(no-pp)))))',
	'MD + VP(V* + S-VP(TO + VP(V* + VP(V* + NP(no-pp) + PP))))'
])


def format_memory(text):
	tree = to_tree(text)
	
	validations = [
		valid_top_level_structure,
		valid_labels
	]
	
	for v in validations:
		if not v(tree): return None

	subj_tree, pred_tree = t[0][0], t[0][1]
	
	chopped_subject = chop_np(subj_tree)
	
	if not chopped_subject:
		return None
	
	if has_restricted_branch(subj_tree) or has_restricted_branch(pred_tree):
		return None
	
	if not format:
		return None

	return True


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
		if isinstance(child, Tree):
			leaves.extend(labeled_leaves(child))
		else:
			leaves.append([tree.label(), child])
	
	return leaves


def chop_np(np):
	assert_label(np, phrases.NOUN_PHRASE)
	
	if not valid_np_children(np):
		return None
	
	subject = {'noun': None, 'owner': None}
	adjs, advs = [], []
	
	noun_set = sp.nouns()
	adj_set = sp.adjectives()
	adv_set = sp.adverbs()
	
	groups = labeled_leaves(np)
	
	i = 0
	for g in groups:
		label, word = g
		
		if not subject['noun'] and label in noun_set:
			subject['noun'] = word
		elif label in adj_set:
			adjs.append(word)
		elif label in adv_set:
			advs.append(word)
		
		if label == words.POSSESSIVE_PRONOUN:
			subject['owner'] = word
			subject['noun'] = None
		elif label == words.POSSESSIVE_ENDING and i > 0:
			subject['owner'] = groups[i - 1][1]
			subject['noun'] = None
			
		i += 1
		
	return {
		'n': subject['noun'],
		'owner': subject['owner'],
		'adjs': adjs,
		'advs': advs
	}


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
		if isinstance(child, Tree):
			labels.append(child.label())
			labels.extend(all_nested_labels(child))
	
	return labels


def to_tree(text):
	return list(parser.raw_parse(text))[0]


def children_with_label(tree, label):
	return [child for child in tree if isinstance(child, Tree) and child.label() == label]


def lemmatize(w, pos='n'):
	return lemmatizer.lemmatize(w, pos=pos)


def is_name(name):
	return bool(names_map.get(name))


def assert_label(tree, label):
	if not isinstance(tree, Tree):
		error('Label Assertion Error: Tree isn\'t even a tree: {}'.format(tree))
		
	if tree.label() != label:
		error('Label Assertion Error: Label was {}; Expected {}.'.format(tree.label(), label))

		
def error(msg=''):
	raise BaseException(msg)