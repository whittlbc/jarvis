import jarvis.helpers.nlp.stanford_parser as sp
from jarvis.helpers.nlp.memory_formats import PREDICATE_FORMATS, RESTRICTED_LABELS
from jarvis.helpers.nlp.lemmatizer import lemmatizer
from jarvis.helpers.nlp.names import names_map
from nltk.tree import Tree
from jarvis import logger
from numpy import random
from jarvis.helpers.models import Models

# Configured instance of the Stanford Parser
parser = sp.parser()

words = sp.words
phrases = sp.phrases
clauses = sp.clauses
nouns = sp.nouns
adjectives = sp.adjectives
adverbs = sp.adverbs
verbs = sp.verbs

models = Models()


def format_memory(text):
	tree = to_tree(text)
	
	validations = [
		valid_top_level_structure,
		valid_labels
	]
	
	for v in validations:
		if not v(tree): 
			return None, None

	subj_tree, pred_tree = tree[0][0], tree[0][1]
	
	subject = chop_np(subj_tree)
	
	if not subject:
		return None, None
	
	# chop_predicate should call the reduce_predicate method
	format, pred_content = chop_predicate(pred_tree)
	
	if format not in PREDICATE_FORMATS:
		return None, None
		
	leading_v_label = pred_content[0].keys()[0]
	
	# if action
	if leading_v_label == 'V*':
		modeled_content = format_modeled_content(pred_content)
	else:
		modeled_content = format_modeled_content(pred_content[1:])
	
	# [
	# 	{
	# 		'action': {
	# 			'v': 'playing',
	# 			'adj': [],
	# 			'adv': [],
	# 			'subject': {
	# 				'owner': None,
	# 				'noun': 'basketball',
	# 				'description': {
	# 					'adv': [],
	# 					'adj': []
	# 				}
	# 			}
	# 		}
	# 	}
	# ]
		
	# Models
	subjects = {}
	rels = {}
	rel_subjects = {}
	rel_rels = {}
	actions = {}
	subj_subj_actions = {}
	rel_subj_actions = {}
	rel_rel_actions = {}
	
	# handle the leading subject first
	lead_subj_type = 'subj'
	lead_subj_noun_uid = uid()
	subjects[lead_subj_noun_uid] = { 'orig': subject['noun'] }
	
	if subject['owner']:
		lead_subj_type = 'rel'
		lead_subj_owner_uid = uid()
		subjects[lead_subj_owner_uid] = {'orig': subject['owner']} # handle 'my' or 'your' instances
		
		lead_subj_rel_uid = uid()
		rels[lead_subj_rel_uid] = {
			'subj_a_uid': lead_subj_owner_uid,
			'subj_b_uid': lead_subj_noun_uid,
			'order': 1	# change to class constants somewhere
		}
	
	# for each grouping
	for data in modeled_content:
		
		if leading_v_label == 'V*':
			if data.get('subject'):
				outer_subj = data['subject']
				
				outer_subj_type = 'subj'
				outer_subj_noun_uid = uid()
				subjects[outer_subj_noun_uid] = {'orig': outer_subj['noun']}
				
				if outer_subj['owner']:
					outer_subj_type = 'rel'
					outer_subj_owner_uid = uid()
					subjects[outer_subj_owner_uid] = {'orig': outer_subj['owner']}
					
					outer_subj_rel_uid = uid()
					rels[outer_subj_rel_uid] = {
						'subj_a_uid': outer_subj_owner_uid,
						'subj_b_uid': outer_subj_noun_uid,
						'order': 1  # change to class constants somewhere
					}
			
			if data.get('action'):
				a = data['action']
				action_uid = uid()
				actions[action_uid] = {'orig': a['v']}
				
				action_subj = a['subject']
				
				action_subj_type = 'subj'
				action_subj_noun_uid = uid()
				subjects[action_subj_noun_uid] = {'orig': action_subj['noun']}
				
				if action_subj['owner']:
					action_subj_type = 'rel'
					action_subj_owner_uid = uid()
					subjects[action_subj_owner_uid] = {'orig': action_subj['owner']}
					
					action_subj_rel_uid = uid()
					rels[action_subj_rel_uid] = {
						'subj_a_uid': action_subj_owner_uid,
						'subj_b_uid': action_subj_noun_uid,
						'order': 1  # change to class constants somewhere
					}
				
				if lead_subj_type == 'subj' and action_subj_type == 'subj':
					subj_subj_action_uid = uid()
					subj_subj_actions[subj_subj_action_uid] = {
						'subj_a_uid': lead_subj_noun_uid,
						'subj_b_uid': action_subj_noun_uid,
						'action_uid': action_uid
					}
					
				elif lead_subj_type == 'rel' and action_subj_type == 'subj':
					rel_subj_action_uid = uid()
					rel_subj_actions[rel_subj_action_uid] = {
						'rel_uid': lead_subj_rel_uid,
						'subject_uid': action_subj_noun_uid,
						'action_uid': action_uid,
						'order': 1
					}
					
				elif lead_subj_type == 'subj' and action_subj_type == 'rel':
					rel_subj_action_uid = uid()
					rel_subj_actions[rel_subj_action_uid] = {
						'rel_uid': action_subj_rel_uid,
						'subject_uid': lead_subj_noun_uid,
						'action_uid': action_uid,
						'order': -1
					}
					
				else:
					rel_rel_action_uid = uid()
					rel_rel_actions[rel_rel_action_uid] = {
						'rel_a_uid': lead_subj_rel_uid,
						'rel_b_uid': action_subj_rel_uid,
						'action_uid': action_uid
					}
					
		else:
			# only subjects and descriptions will exists here...
			
			if data.get('subject'):
				outer_subj = data['subject']
				
				outer_subj_type = 'subj'
				outer_subj_noun_uid = uid()
				subjects[outer_subj_noun_uid] = {'orig': outer_subj['noun']}
				
				if outer_subj['owner']:
					outer_subj_type = 'rel'
					outer_subj_owner_uid = uid()
					subjects[outer_subj_owner_uid] = {'orig': outer_subj['owner']}
					
					outer_subj_rel_uid = uid()
					rels[outer_subj_rel_uid] = {
						'subj_a_uid': outer_subj_owner_uid,
						'subj_b_uid': outer_subj_noun_uid,
						'order': 1  # change to class constants somewhere
					}
				
				if lead_subj_type == 'subj' and outer_subj_type == 'subj':
					rel_uid = uid()
					
					if leading_v_label == 'V(BE)':
						order = 0
					else:
						order = 1
						
					rels[rel_uid] = {
						'subj_a_uid': lead_subj_noun_uid,
						'subj_b_uid': outer_subj_noun_uid,
						'order': order
					}
					
				elif lead_subj_type == 'rel' and outer_subj_type == 'subj':
					rel_subj_uid = uid()
					
					if leading_v_label == 'V(BE)':
						order = 0
					else:
						order = 1
						
					rel_subjects[rel_subj_uid] = {
						'rel_uid': lead_subj_rel_uid,
						'subject_uid': outer_subj_noun_uid,
						'order': order
					}
					
				elif lead_subj_type == 'subj' and outer_subj_type == 'rel':
					rel_subj_uid = uid()
					
					if leading_v_label == 'V(BE)':
						order = 0
					else:
						order = -1
						
					rel_subjects[rel_subj_uid] = {
						'rel_uid': outer_subj_rel_uid,
						'subject_uid': lead_subj_noun_uid,
						'order': order
					}
					
				else:
					rel_rel_uid = uid()
					
					if leading_v_label == 'V(BE)':
						order = 0
					else:
						order = 1
						
					rel_rels[rel_rel_uid] = {
						'rel_a_uid': lead_subj_rel_uid,
						'rel_b_uid': outer_subj_rel_uid,
						'order': order
					}
				
	
	# Subjects
	subj_uid_id_map = upsert_subjects(subjects)
	
	# Rels
	rel_uid_id_map = upsert_rels(rels, subj_uid_id_map)
	rel_subj_uid_id_map = upsert_rel_subjects(rel_subjects, subj_uid_id_map, rel_uid_id_map)
	rel_rel_uid_id_map = upsert_rel_rels(rel_rels, rel_uid_id_map)
	
	# Actions
	actions_uid_id_map = upsert_actions(actions)
	subj_subj_actions_uid_id_map = upsert_subj_subj_actions(subj_subj_actions, actions_uid_id_map, subj_uid_id_map)
	rel_subj_actions_uid_id_map = upsert_rel_subj_actions(rel_subj_actions, actions_uid_id_map, subj_uid_id_map, rel_uid_id_map)
	rel_rel_actions_uid_id_map = upsert_rel_rel_actions(rel_rel_actions, actions_uid_id_map, rel_uid_id_map)
	
	# Need to send back info about what was saved so that Jarvis can reiterate that to the user
	return None, None


def upsert_subjects(subjects):
	uid_id_map = {}
	
	for k, v in subjects.items():
		data = {
			'lower': v['orig'].lower(),
			'orig': v['orig']
		}
				
		id = upsert(models.SUBJECT, data)
		uid_id_map[k] = id
		
	return uid_id_map


def upsert_rels(rels, subj_uid_id_map):
	uid_id_map = {}

	for k, v in rels.items():
		data = {
			'a_id': subj_uid_id_map[v['subj_a_uid']],
			'b_id': subj_uid_id_map[v['subj_b_uid']],
			'order': v['order']
		}
		
		id = upsert(models.REL, data)
		uid_id_map[k] = id
		
	return uid_id_map


def upsert_rel_subjects(rel_subjects, subj_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rel_subjects.items():
		data = {
			'rel_id': rel_uid_id_map[v['rel_uid']],
			'subject_id': subj_uid_id_map[v['subject_uid']],
			'order': v['order']
		}
		
		id = upsert(models.REL_SUBJECT, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_rel_rels(rel_rels, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rel_rels.items():
		data = {
			'a_id': rel_uid_id_map[v['rel_a_uid']],
			'b_id': rel_uid_id_map[v['rel_b_uid']],
			'order': v['order']
		}
		
		id = upsert(models.REL_REL, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_actions(actions):
	uid_id_map = {}
	
	for k, v in actions.items():
		data = {
			'lower': v['orig'].lower(),
			'orig': v['orig']
		}
		
		id = upsert(models.ACTION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_subj_subj_actions(subj_subj_actions, actions_uid_id_map, subj_uid_id_map):
	uid_id_map = {}
	
	for k, v in subj_subj_actions.items():
		data = {
			'a_id': subj_uid_id_map[v['subj_a_uid']],
			'b_id': subj_uid_id_map[v['subj_b_uid']],
			'action_id': actions_uid_id_map[v['action_uid']]
		}
		
		id = upsert(models.SUBJECT_SUBJECT_ACTION, data)
		uid_id_map[k] = id
	
	return uid_id_map
	
	
def upsert_rel_subj_actions(rel_subj_actions, actions_uid_id_map, subj_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rel_subj_actions.items():
		data = {
			'rel_id': rel_uid_id_map[v['rel_uid']],
			'subject_id': subj_uid_id_map[v['subject_uid']],
			'action_id': actions_uid_id_map[v['action_uid']],
			'order': v['order']
		}
		
		id = upsert(models.REL_SUBJECT_ACTION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_rel_rel_actions(rel_rel_actions, actions_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rel_rel_actions.items():
		data = {
			'a_id': rel_uid_id_map[v['rel_a_uid']],
			'b_id': rel_uid_id_map[v['rel_b_uid']],
			'action_id': actions_uid_id_map[v['action_uid']]
		}
		
		id = upsert(models.REL_REL_ACTION, data)
		uid_id_map[k] = id
	
	return uid_id_map

	
def format_modeled_content(data):
	modeled_data = []
	content = {}
		
	for child in data:
		if isinstance(child, list):
			modeled_data.extend(format_modeled_content(child))
			return modeled_data
		else:
			key = child.keys()[0]
			val = child[key]
			
			if key == 'V*':
				content['action'] = {
					'v': val,
					'adj': [],
					'adv': []
				}
				
			elif key == 'NP':
				if content.get('action'):
					content['action']['subject'] = val
				else:
					content['subject'] = val
			
	modeled_data.append(content)
			
	return modeled_data


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

# TODO: Add a correction for 'your' that maps to the bot's name
def corrected_owner(owner):
	if owner.lower() in ['my', 'our']:
		return 'I'
	else:
		return owner
	
	
def chop_predicate(tree):
	format = []
	format_content = []
	
	for child in tree:
		if is_tree(child):
			label = child.label()
			
			if label in [phrases.ADJ_PHRASE, phrases.ADV_PHRASE]:
				pass
			
			elif label in [clauses.DECLARATION, phrases.VERB_PHRASE]:
				f = {}
				f[label], fc = chop_predicate(child)
				
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


def uid():
	return str(random.random())[2:]


def upsert(model, data):
	# upsert that shit
	print('Upserting {}: {}'.format(model, data))
	return 1  # id