import jarvis.helpers.nlp.stanford_parser as sp
from jarvis.helpers.nlp.memory_formats import STORAGE_PREDICATE_FORMATS, WH_RETRIEVAL_PREDICATE_FORMATS, RESTRICTED_LABELS
from jarvis.helpers.nlp.lemmatizer import lemmatizer
from jarvis.helpers.nlp.names import names_map
from jarvis.helpers.helpers import corrected_owner, format_possession, and_join
from nltk.tree import Tree
from jarvis import logger
from numpy import random
from jarvis.helpers.models import Models
from jarvis.helpers.pg import upsert, keyify, find

# Configured instance of the Stanford Parser
parser = sp.parser()

words = sp.words
phrases = sp.phrases
clauses = sp.clauses
special = sp.special
nouns = sp.nouns
adjectives = sp.adjectives
adverbs = sp.adverbs
verbs = sp.verbs
modals = sp.modals

models = Models()


################################
# STORAGE
################################

def format_memory(text):
	text = strip_trailing_punc(text)
	tree = to_tree(text)
	
	tree_validations = [
		valid_storage_format,
		valid_labels
	]
	
	for v in tree_validations:
		if not v(tree): 
			return False

	subj_tree, pred_tree = tree[0]
	
	subject = chop_np(subj_tree)
	
	if not subject:
		return False
	
	# chop_predicate should call the reduce_predicate method
	format, pred_content = chop_predicate(pred_tree)
	
	if format not in STORAGE_PREDICATE_FORMATS:
		return False
	
	leading_v_label = pred_content[0].keys()[0]
	
	# if action
	if leading_v_label == 'V*':
		modeled_content = format_modeled_content(pred_content)
	else:
		modeled_content = format_modeled_content(pred_content[1:])

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
		subjects[lead_subj_owner_uid] = {'orig': subject['owner']}
		
		lead_subj_rel_uid = uid()
		rels[lead_subj_rel_uid] = {
			'subj_a_uid': lead_subj_owner_uid,
			'subj_b_uid': lead_subj_noun_uid,
			'relation': 1	# change to class constants somewhere
		}
	
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
						'relation': 1  # change to class constants somewhere
					}
			
			if data.get('action'):
				a = data['action']
				action_uid = uid()
				actions[action_uid] = {'verb': a['v']}
				
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
						'relation': 1  # change to class constants somewhere
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
						'direction': 1
					}
					
				elif lead_subj_type == 'subj' and action_subj_type == 'rel':
					rel_subj_action_uid = uid()
					rel_subj_actions[rel_subj_action_uid] = {
						'rel_uid': action_subj_rel_uid,
						'subject_uid': lead_subj_noun_uid,
						'action_uid': action_uid,
						'direction': -1
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
				det = outer_subj['det']
					
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
						'relation': 1  # change to class constants somewhere
					}
				
				if lead_subj_type == 'subj' and outer_subj_type == 'subj':
					rel_uid = uid()
					
					if leading_v_label == 'V(BE)':
						if det and det.lower() in ['a', 'an']:
							order = 2
						else:
							order = 0
					else:
						order = 1
						
					rels[rel_uid] = {
						'subj_a_uid': lead_subj_noun_uid,
						'subj_b_uid': outer_subj_noun_uid,
						'relation': order
					}
					
				elif lead_subj_type == 'rel' and outer_subj_type == 'subj':
					rel_subj_uid = uid()
					
					if leading_v_label == 'V(BE)':
						if det and det.lower() in ['a', 'an']:
							order = 2
						else:
							order = 0
					else:
						order = 1
						
					rel_subjects[rel_subj_uid] = {
						'rel_uid': lead_subj_rel_uid,
						'subject_uid': outer_subj_noun_uid,
						'relation': order
					}
					
				elif lead_subj_type == 'subj' and outer_subj_type == 'rel':
					rel_subj_uid = uid()
					
					if leading_v_label == 'V(BE)':
						if det and det.lower() in ['a', 'an']:
							order = 2
						else:
							order = 0
					else:
						order = -1
						
					rel_subjects[rel_subj_uid] = {
						'rel_uid': outer_subj_rel_uid,
						'subject_uid': lead_subj_noun_uid,
						'relation': order
					}
					
				else:
					rel_rel_uid = uid()
					
					if leading_v_label == 'V(BE)':
						if det and det.lower() in ['a', 'an']:
							order = 2
						else:
							order = 0
					else:
						order = 1
						
					rel_rels[rel_rel_uid] = {
						'rel_a_uid': lead_subj_rel_uid,
						'rel_b_uid': outer_subj_rel_uid,
						'relation': order
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
	
	return True
	

def upsert_subjects(subjects):
	uid_id_map = {}
	
	for k, v in subjects.items():
		data = {
			'lower': v['orig'].lower(),
			'orig': v['orig']
		}
				
		id = upsert(models.SUBJECT, data, unique_to=['lower'])
		uid_id_map[k] = id
		
	return uid_id_map


def upsert_rels(rels, subj_uid_id_map):
	uid_id_map = {}

	for k, v in rels.items():
		data = {
			'a_id': subj_uid_id_map[v['subj_a_uid']],
			'b_id': subj_uid_id_map[v['subj_b_uid']],
			'relation': v['relation']
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
			'relation': v['relation']
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
			'relation': v['relation']
		}
		
		id = upsert(models.REL_REL, data)
	
	return uid_id_map


def upsert_actions(actions):
	uid_id_map = {}
	
	for k, v in actions.items():
		data = {
			'verb': lemmatize(v['verb'].lower(), pos='v')
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
			'direction': v['direction']
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


def valid_storage_format(t):
	return t[0].label() == clauses.DECLARATION \
		and len(t[0]) == 2 \
		and t[0][0].label() == phrases.NOUN_PHRASE \
		and t[0][1].label() == phrases.VERB_PHRASE
	
	
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
	elif lemmatized_verb == 'do':
		return 'V(DO)'
	else:
		return 'V*'
	
	
################################
# RETRIEVAL
################################

def query_memory(text):
	answer = None
	text = strip_trailing_punc(text) + '?'
	
	if lemmatize(text.split()[0].lower(), pos='v') == 'do':
		text = ' '.join(['Did'] + text.split()[1:])
	
	tree = to_tree(text)
	
	if is_direct_wh_query(tree):
		answer = handle_wh_query(strip_last_branch(tree), 'direct')
		
	elif is_relative_wh_query(tree):
		answer = handle_wh_query(strip_last_branch(tree), 'relative')
		
	elif is_yes_no_query(tree, text):
		answer = handle_yes_no_query(strip_last_branch(tree))
	
	return answer


def is_direct_wh_query(t):
	return t[0].label() == clauses.DIRECT_WH_QUESTION \
		and len(t[0]) == 3 \
		and t[0][0].label() in [phrases.WH_NOUN_PHRASE, phrases.WH_ADV_PHRASE] \
		and t[0][1].label() == clauses.INVERTED_YES_NO \
		and t[0][2].label() == special.PUNC
	

# any examples of this? --> can we somehow morph it into the ^above structure?
def is_relative_wh_query(t):
	return t[0].label() == clauses.RELATIVE_CLAUSE \
		and len(t[0]) == 3 \
		and t[0][0].label() == phrases.WH_NOUN_PHRASE \
		and t[0][1].label() == clauses.DECLARATION \
		and t[0][2].label() == special.PUNC


def is_yes_no_query(tree, text):
	lead_word = text.split()[0].lower()
	lead_word_prompts_yn = lemmatize(lead_word, pos='v') in ['be', 'do'] or lead_word in modals
	
	return lead_word_prompts_yn \
	  and tree[0].label() == clauses.INVERTED_YES_NO \
		and len(tree[0]) in [3, 4] \
		and tree[0][len(tree[0]) - 1].label() == special.PUNC


def handle_wh_query(tree, q_type):
	wh_tree, q_tree = tree[0]
	wh_info = chop_wh(wh_tree)
	
	if not wh_info: return False
	
	if q_type == 'direct':
		format, q_content = chop_predicate(q_tree)
		
		if format not in WH_RETRIEVAL_PREDICATE_FORMATS: return False
		
		leading_v = first_of_label(q_content)
		
		if not leading_v: return False
		
		leading_v_label = leading_v.keys()[0]
		
		if leading_v_label == 'V(DO)':
			return fetch_wh_do(q_content, wh_info)
		
		if leading_v_label == 'V*':  # Action
			modeled_content = format_modeled_content(q_content)
		else:  # V(BE) or V(OWN)
			modeled_content = format_modeled_content(q_content[1:])
		
		return fetch_memory_wh(modeled_content, wh_info, leading_v_label)
		
	elif q_type == 'relative':
		format, q_content = chop_relative_q(q_tree)
	else:
		error('q_type not valid while handling WH mem query: {}'.format(q_type))


def fetch_wh_do(q_content, wh_info):
	np = first_of_label(q_content, label=phrases.NOUN_PHRASE)
	
	if not np:
		error('WH-DO query has no NP for some reason...{}'.format(tree))
	
	sub_lists = [l for l in q_content if isinstance(l, list)]
	
	if not sub_lists:
		error('WH-DO query has no VP for some reason...{}'.format(tree))
	
	action = {}
	
	for child in sub_lists[0]:  # the first VP
		label, val = child.items()[0]
		
		if label == 'V*' and not action:
			action['v'] = val
			
		# TODO: Will need to handle V(BE) and V(OWN)'s here as well
			
		elif label == phrases.NOUN_PHRASE and action:
			action['subject'] = val
	
	if action:
		action['adj'] = []
		action['adv'] = []
		subject = np.values()[0]
		
		if wh_info['wh'] in ['when', 'where']:
			return handle_whadvp_do(subject, action, wh_info)
		else:
			return handle_whnp_do(subject, action, wh_info)
		
	return None


def handle_whadvp_do(subject, action, wh_info):
	wh = wh_info['wh']
	# TODO: errthang
	return None


# Ex: What do I play?
# Use subject as leading subject and assume that action doesn't have a 'subject' property
# TODO: Still need to figure out how to deal with possessive wh_info's
def handle_whnp_do(subject, action, wh_info):
	subjects = {}
	rels = {}
	actions = {}
	
	lead_subj_type = 'subj'
	lead_subj_noun_uid = uid()
	subjects[lead_subj_noun_uid] = {'orig': subject['noun']}
	
	if subject['owner']:
		lead_subj_type = 'rel'
		lead_subj_owner_uid = uid()
		subjects[lead_subj_owner_uid] = {'orig': subject['owner']}
		
		lead_subj_rel_uid = uid()
		rels[lead_subj_rel_uid] = {
			'subj_a_uid': lead_subj_owner_uid,
			'subj_b_uid': lead_subj_noun_uid,
			'relation': 1  # change to class constants somewhere
		}
	
	action_uid = uid()
	actions[action_uid] = {'verb': action['v']}
	
	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
	actions_uid_query_map = action_query_map(actions)

	result = []

	if lead_subj_type == 'subj':
		ss_uid_info = {
			'subj_a_uid': lead_subj_noun_uid,
			'subj_b_uid': wh_info['wh'],
			'action_uid': action_uid
		}
		
		rs_uid_info = {
			'rel_uid': wh_info['wh'],
			'subject_uid': lead_subj_noun_uid,
			'action_uid': action_uid
		}
		
		ssa_results = find_models_through_ssa(
			ss_uid_info,
			actions_uid_query_map,
			subj_uid_query_map
		)

		rsa_results = find_models_through_rsa(
			rs_uid_info,
			actions_uid_query_map,
			subj_uid_query_map,
			rel_uid_query_map,
			dir=-1
		)
		
		result += [corrected_owner(r) for r in ssa_results]
		
		for group in rsa_results['rels']:
			result.append(format_possession([corrected_owner(g) for g in group]))
		
	else:  # lead_subj_type = 'rel'
		rs_uid_info = {
			'rel_uid': lead_subj_rel_uid,
			'subject_uid': wh_info['wh'],
			'action_uid': action_uid
		}
		
		rr_uid_info = {
			'rel_a_uid': lead_subj_rel_uid,
			'rel_b_uid': wh_info['wh'],
			'action_uid': action_uid
		}

		rsa_results = find_models_through_rsa(
			rs_uid_info,
			actions_uid_query_map,
			subj_uid_query_map,
			rel_uid_query_map,
			dir=1
		)
			
		rra_results = find_models_through_rra(
			rr_uid_info,
			actions_uid_query_map,
			rel_uid_query_map
		)
		
		result += [corrected_owner(r) for r in rsa_results['subjects']]
				
		for group in rra_results:
			result.append(format_possession([corrected_owner(g) for g in group]))
	
	return and_join(result)


def fetch_do_yn(q_content):
	np = first_of_label(q_content, label=phrases.NOUN_PHRASE)
	
	if not np:
		error('WH-DO query has no NP for some reason...{}'.format(tree))
	
	sub_lists = [l for l in q_content if isinstance(l, list)]
	
	if not sub_lists:
		error('WH-DO query has no VP for some reason...{}'.format(tree))
	
	action = {}
	
	for child in sub_lists[0]:  # the first VP
		label, val = child.items()[0]
		
		if label == 'V*' and not action:
			action['v'] = val
		
		# TODO: Will need to handle V(BE) and V(OWN)'s here as well
		
		elif label == phrases.NOUN_PHRASE and action:
			action['subject'] = val
	
	if action:
		action['adj'] = []
		action['adv'] = []
		subject = np.values()[0]
		
		all_eq_subjs = find_all_subj_eqs(subject)
		
		for s in all_eq_subjs:
			result = handle_do_yn_action(s, action)
			
			if result == 'Yes':
				return result
	
	return 'No'


def find_all_subj_eqs(subject):
	eq_subjects = [subject]
	subjects = {}
	rels = {}
	
	lead_subj_type = 'subj'
	lead_subj_noun_uid = uid()
	subjects[lead_subj_noun_uid] = {'orig': subject['noun']}
	
	if subject['owner']:
		lead_subj_type = 'rel'
		lead_subj_owner_uid = uid()
		subjects[lead_subj_owner_uid] = {'orig': subject['owner']}
		
		lead_subj_rel_uid = uid()
		rels[lead_subj_rel_uid] = {
			'subj_a_uid': lead_subj_owner_uid,
			'subj_b_uid': lead_subj_noun_uid,
			'relation': 1
		}
		
		rs_uid_info = {
			'rel_uid': lead_subj_rel_uid,
			'subject_uid': 'wh*'
		}
		
		rr_uid_info = [
			{
				'rel_a_uid': lead_subj_rel_uid,
				'rel_b_uid': 'wh*'
			},
			{
				'rel_a_uid': 'wh*',
				'rel_b_uid': lead_subj_rel_uid
			}
		]
		
		subj_uid_query_map = subject_query_map(subjects)
		rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
		
		rs_result = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=0
		)
		
		for s in rs_result['subjects']:
			eq_subjects.append({
				'owner': None,
				'noun': s,
				'description': {'adv': [], 'adj': []}
			})
			
		for info in rr_uid_info:
			rr_result = find_models_through_rr(
				info,
				rel_uid_query_map,
				relation=0
			)
			
			for r in rr_result:
				eq_subjects.append({
					'owner': r[0],
					'noun': r[1],
					'description': {'adv': [], 'adj': []}
				})
	else:
		r_uid_info = [
			{
				'subj_a_uid': lead_subj_noun_uid,
				'subj_b_uid': 'wh*',
			},
			{
				'subj_a_uid': 'wh*',
				'subj_b_uid': lead_subj_noun_uid,
			}
		]
		
		rs_uid_info = {
			'rel_uid': 'wh*',
			'subject_uid': lead_subj_noun_uid,
		}
		
		subj_uid_query_map = subject_query_map(subjects)
		rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
		
		for info in r_uid_info:
			r_result = find_models_through_r(
				info,
				subj_uid_query_map,
				relation=0
			)
			
			for s in r_result:
				eq_subjects.append({
					'owner': None,
					'noun': s,
					'description': {'adv': [], 'adj': []}
				})
		
		rs_result = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=0
		)
		
		for r in rs_result['rels']:
			eq_subjects.append({
				'owner': r[0],
				'noun': r[1],
				'description': {'adv': [], 'adj': []}
			})
	
	return eq_subjects
	

def handle_do_yn_action(subject, action):
	subjects = {}
	rels = {}
	actions = {}
	
	lead_subj_type = 'subj'
	lead_subj_noun_uid = uid()
	subjects[lead_subj_noun_uid] = {'orig': subject['noun']}
	
	if subject['owner']:
		lead_subj_type = 'rel'
		lead_subj_owner_uid = uid()
		subjects[lead_subj_owner_uid] = {'orig': subject['owner']}
		
		lead_subj_rel_uid = uid()
		rels[lead_subj_rel_uid] = {
			'subj_a_uid': lead_subj_owner_uid,
			'subj_b_uid': lead_subj_noun_uid,
			'relation': 1  # change to class constants somewhere
		}
		
	action_uid = uid()
	actions[action_uid] = {'verb': action['v']}
	
	action_subj = action.get('subject')
	action_subj_type = None
	
	if action_subj and action_subj['noun'].lower() not in ['anything', 'anyone']:
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
				'relation': 1  # change to class constants somewhere
			}
		
	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
	actions_uid_query_map = action_query_map(actions)
	
	answer = 'No'
	
	if lead_subj_type == 'subj':
		if not action_subj_type:
			ss_uid_info = {
				'subj_a_uid': lead_subj_noun_uid,
				'subj_b_uid': '*',
				'action_uid': action_uid
			}
			
			rs_uid_info = {
				'rel_uid': '*',
				'subject_uid': lead_subj_noun_uid,
				'action_uid': action_uid
			}
			
			ssa_results = find_models_through_ssa(
				ss_uid_info,
				actions_uid_query_map,
				subj_uid_query_map
			)
			
			rsa_results = find_models_through_rsa(
				rs_uid_info,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=-1
			)
			
			if ssa_results or rsa_results['rsa_results']:
				answer = 'Yes'
			
		elif action_subj_type == 'subj':
			ss_uid_info = {
				'subj_a_uid': lead_subj_noun_uid,
				'subj_b_uid': action_subj_noun_uid,
				'action_uid': action_uid
			}
			
			ssa_results = find_models_through_ssa(
				ss_uid_info,
				actions_uid_query_map,
				subj_uid_query_map
			)
			
			if ssa_results:
				answer = 'Yes'
				
		elif action_subj_type == 'rel':
			rs_uid_info = {
				'rel_uid': action_subj_rel_uid,
				'subject_uid': lead_subj_noun_uid,
				'action_uid': action_uid
			}
			
			rsa_results = find_models_through_rsa(
				rs_uid_info,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=-1
			)
			
			if rsa_results['rsa_results']:
				answer = 'Yes'
			
	else:  # lead_subj_type = 'rel'
		if not action_subj_type:
			rs_uid_info = {
				'rel_uid': lead_subj_rel_uid,
				'subject_uid': '*',
				'action_uid': action_uid
			}
			
			rr_uid_info = {
				'rel_a_uid': lead_subj_rel_uid,
				'rel_b_uid': '*',
				'action_uid': action_uid
			}
			
			rsa_results = find_models_through_rsa(
				rs_uid_info,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=1
			)
			
			rra_results = find_models_through_rra(
				rr_uid_info,
				actions_uid_query_map,
				rel_uid_query_map
			)
		
			if rsa_results['rsa_results'] or rra_results:
				answer = 'Yes'
				
		elif action_subj_type == 'subj':
			rs_uid_info = {
				'rel_uid': lead_subj_rel_uid,
				'subject_uid': action_subj_noun_uid,
				'action_uid': action_uid
			}
			
			rsa_results = find_models_through_rsa(
				rs_uid_info,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=1
			)
			
			if rsa_results['rsa_results']:
				answer = 'Yes'
			
		elif action_subj_type == 'rel':
			rr_uid_info = {
				'rel_a_uid': lead_subj_rel_uid,
				'rel_b_uid': action_subj_rel_uid,
				'action_uid': action_uid
			}
			
			rra_results = find_models_through_rra(
				rr_uid_info,
				actions_uid_query_map,
				rel_uid_query_map
			)
			
			if rra_results:
				answer = 'Yes'
				
	return answer


def fetch_memory_wh(modeled_content, wh_info, leading_v_label):
	subjects = {}
	rels = {}
	rel_subjects = {}
	rel_rels = {}
	actions = {}
	subj_subj_actions = {}
	rel_subj_actions = {}
	rel_rel_actions = {}
	
	inner_subj_type = None
		
	for data in modeled_content:
		if leading_v_label == 'V*':  # ACTION
			a = data['action']
			action_uid = uid()
			actions[action_uid] = {'verb': a['v']}
			
			action_subj = a.get('subject')
			action_subj_type = None
			
			if action_subj:
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
						'relation': 1  # change to class constants somewhere
					}
				
				if action_subj_type == 'subj':
					subj_subj_action_uid = uid()
					subj_subj_actions[subj_subj_action_uid] = {
						'subj_a_uid': wh_info['wh'],
						'subj_b_uid': action_subj_noun_uid,
						'action_uid': action_uid
					}
				else:
					rel_subj_action_uid = uid()
					rel_subj_actions[rel_subj_action_uid] = {
						'rel_uid': action_subj_rel_uid,
						'subject_uid': wh_info['wh'],
						'action_uid': action_uid,
						'direction': -1
					}
		
		else:  # V(BE) or V(OWN) relations
			if data.get('subject'):  # type of rel exists
				inner_subj = data['subject']

				inner_subj_type = 'subj'
				inner_subj_noun_uid = uid()
				subjects[inner_subj_noun_uid] = {'orig': inner_subj['noun']}

				if inner_subj['owner']:
					inner_subj_type = 'rel'
					inner_subj_owner_uid = uid()
					subjects[inner_subj_owner_uid] = {'orig': inner_subj['owner']}

					inner_subj_rel_uid = uid()
					rels[inner_subj_rel_uid] = {
						'subj_a_uid': inner_subj_owner_uid,
						'subj_b_uid': inner_subj_noun_uid,
						'relation': 1
					}

	result = []

	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
			
	if actions:
		actions_uid_query_map = action_query_map(actions)
		
		if action_subj_type == 'subj':  # Ex: Who plays basketball?
			# query SubjectSubjectActions and RelSubjectActions
				
			# Since action_subj_type = 'subj', subj_subj_actions must exist since this is a query
			ss_uid_info = subj_subj_actions.values()[0]
			wh = ss_uid_info['subj_a_uid']  # we know this is the WH word since A is the unknown
			rs_uid_info = {
				'rel_uid': wh,
				'subject_uid': ss_uid_info['subj_b_uid'],
				'action_uid': ss_uid_info['action_uid']
			}
			
			ssa_results = find_models_through_ssa(
				ss_uid_info,
				actions_uid_query_map,
				subj_uid_query_map
			)
		
			rsa_results = find_models_through_rsa(
				rs_uid_info,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=1,	# We know it's 1 since rel is the unknown
			)
			
			result += [corrected_owner(r) for r in ssa_results]
			
			for group in rsa_results['rels']:
				result.append(format_possession([corrected_owner(g) for g in group]))
		
		elif action_subj_type == 'rel':  # Ex: Who played my game?
			# query RelRelActions and RelSubjectActions
			
			# Since action_subj_type = 'rel', rel_subj_actions must exist since this is a query
			rs_uid_info = rel_subj_actions.values()[0]
			wh = rs_uid_info['subject_uid']  # we know this is the WH word since A is the unknown
			rr_uid_info = {
				'rel_a_uid': wh,
				'rel_b_uid': rs_uid_info['rel_uid'],
				'action_uid': rs_uid_info['action_uid']
			}
			
			rsa_results = find_models_through_rsa(
				rs_uid_info,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=-1,  # We know it's 1 since rel is the unknown
			)
			
			rra_results = find_models_through_rra(
				rr_uid_info,
				actions_uid_query_map,
				rel_uid_query_map
			)
						
			for group in rsa_results['rels'] + rra_results:
				result.append(format_possession([corrected_owner(g) for g in group]))
				
		else:  # Ex: Who played?
			# query SubjectSubjectAction, RelSubjectAction, RelRelAction
			
			action_uid = actions_uid_query_map.keys()[0]
			
			ss_uid_info = {
				'subj_a_uid': wh_info['wh'],
				'subj_b_uid': '*',
				'action_uid': action_uid
			}
			
			rs_uid_info_forward = {
				'rel_uid': wh_info['wh'],
				'subject_uid': '*',
				'action_uid': action_uid
			}
			
			rs_uid_info_backward = {
				'rel_uid': '*',
				'subject_uid': wh_info['wh'],
				'action_uid': action_uid
			}
			
			rr_uid_info = {
				'rel_a_uid': wh_info['wh'],
				'rel_b_uid': '*',
				'action_uid': action_uid
			}
			
			ssa_results = find_models_through_ssa(
				ss_uid_info,
				actions_uid_query_map,
				subj_uid_query_map
			)
			
			rsa_results_forward = find_models_through_rsa(
				rs_uid_info_forward,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=1,
			)
			
			rsa_results_backward = find_models_through_rsa(
				rs_uid_info_backward,
				actions_uid_query_map,
				subj_uid_query_map,
				rel_uid_query_map,
				dir=-1,
			)
			
			rra_results = find_models_through_rra(
				rr_uid_info,
				actions_uid_query_map,
				rel_uid_query_map
			)
	
			result += [corrected_owner(r) for r in ssa_results]
			
			for group in rsa_results_forward['rels'] + rsa_results_backward['rels'] + rra_results:
				result.append(format_possession([corrected_owner(g) for g in group]))
	
	else:
		if leading_v_label == 'V(BE)':
			if inner_subj_type == 'subj':
				r_uid_info = [
					{
						'subj_a_uid': wh_info['wh'],
						'subj_b_uid': inner_subj_noun_uid,
						'relation': 0
					},
					{
						'subj_a_uid': inner_subj_noun_uid,
						'subj_b_uid': wh_info['wh'],
						'relation': 0
					},
					{
						'subj_a_uid': inner_subj_noun_uid,
						'subj_b_uid': wh_info['wh'],
						'relation': 2
					}
				]
				
				rs_uid_info = {
					'rel_uid': wh_info['wh'],
					'subject_uid': inner_subj_noun_uid
				}
				
				r_results_eq = []
				r_results_pc = []
				for info in r_uid_info:
					r_result = find_models_through_r(
						info,
						subj_uid_query_map,
						relation=info['relation']
					)
					
					if info['relation'] == 0:
						r_results_eq += [corrected_owner(r) for r in r_result]
					elif info['relation'] == 2:
						r_results_pc += [corrected_owner(r) for r in r_result]
				
				result += r_results_eq
				
				rs_results = find_models_through_rs(
					rs_uid_info,
					subj_uid_query_map,
					rel_uid_query_map,
					relation=0
				)
				
				for group in rs_results['rels']:
					result.append(format_possession([corrected_owner(g) for g in group]))
			
				# If no EQ relations, only then add the PC relations
				if not result:
					result += [add_det_prefix(r) for r in r_results_pc]
			
			elif inner_subj_type == 'rel':
				rs_uid_info = [
					{
						'rel_uid': inner_subj_rel_uid,
						'subject_uid': wh_info['wh'],
						'relation': 0
					},
					{
						'rel_uid': inner_subj_rel_uid,
						'subject_uid': wh_info['wh'],
						'relation': 2
					}
				]
				
				rr_uid_info = [
					{
						'rel_a_uid': wh_info['wh'],
						'rel_b_uid': inner_subj_rel_uid,
						'relation': 0
					},
					{
						'rel_a_uid': inner_subj_rel_uid,
						'rel_b_uid': wh_info['wh'],
						'relation': 0
					}
				]
				
				rs_results_eq = []
				rs_results_pc = []
				for info in rs_uid_info:
					rs_result = find_models_through_rs(
						info,
						subj_uid_query_map,
						rel_uid_query_map,
						relation=info['relation']
					)
					
					if info['relation'] == 0:
						rs_results_eq += [corrected_owner(r) for r in r_result['subjects']]
					elif info['relation'] == 2:
						rs_results_pc += [corrected_owner(r) for r in r_result['subjects']]
				
				result += rs_results_eq
				
				for info in rr_uid_info:
					rr_result = find_models_through_rr(
						info,
						rel_uid_query_map,
						relation=info['relation']
					)
					
					for group in rr_result:
						result.append(format_possession([corrected_owner(g) for g in group]))
				
				# If no EQ relations, only then add the PC relations
				if not result:
					result += [add_det_prefix(r) for r in rs_results_pc]
					
			else:
				# description handler
				print

		elif leading_v_label == 'V(OWN)':
			# TODO
			print
	
	return and_join(result)


def select_where(model, returning='*'):
	return 'SELECT {} FROM {} WHERE'.format(returning, model)


def subject_query_map(subjects):
	uid_query_map = {}
	query = select_where(models.SUBJECT, returning='id')
	
	for k, v in subjects.items():
		data = {
			'lower': v['orig'].lower()
		}
		
		uid_query_map[k] = '{} {}'.format(query, keyify(data, connector=' AND '))
	
	return uid_query_map


def rel_query_map(rels, subj_uid_query_map):
	uid_query_map = {}
	query = select_where(models.REL, returning='id')

	keys_map = {
		'a_id': 'subj_a_uid',
		'b_id': 'subj_b_uid'
	}
	
	for k, v in rels.items():
		data = {
			'relation': v['relation']
		}
		
		for key, val in keys_map.items():
			if subj_uid_query_map.get(v[val]):
				data[key] = '({})'.format(subj_uid_query_map.get(v[val]))
			else:
				# Deal with direct-rel queries later
				print
		
		uid_query_map[k] = '{} {}'.format(query, keyify(data, connector=' AND '))
	
	return uid_query_map


def action_query_map(actions):
	uid_query_map = {}
	query = select_where(models.ACTION, returning='id')
	
	for k, v in actions.items():
		data = {
			'verb': lemmatize(v['verb'].lower(), pos='v')
		}
		
		uid_query_map[k] = '{} {}'.format(query, keyify(data, connector=' AND '))
	
	return uid_query_map


def find_models_through_r(r_info, subj_uid_query_map, relation=None):
	query_keys_map = {
		'a_id': [subj_uid_query_map, 'subj_a_uid', models.SUBJECT],
		'b_id': [subj_uid_query_map, 'subj_b_uid', models.SUBJECT]
	}
	
	data = {}
	
	if relation != None:
		data['relation'] = relation
	
	r_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = r_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				r_return_col = key
				query_model = model
	
	if not query_model:
		return find(models.REL, data)
	
	r_query_prefix = select_where(models.REL, returning=r_return_col)
	r_query = '{} {}'.format(r_query_prefix, keyify(data, connector=' AND '))
	
	results = find(query_model, {'id': '({})'.format(r_query)}, returning='orig')
	
	return [r[0] for r in results]


def find_models_through_rs(rs_info, subj_uid_query_map, rel_uid_query_map, relation=None):
	query_keys_map = {
		'rel_id': [rel_uid_query_map, 'rel_uid', models.REL],
		'subject_id': [subj_uid_query_map, 'subject_uid', models.SUBJECT]
	}
	
	data = {}
	
	if relation != None:
		data['relation'] = relation
	
	rs_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rs_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				rs_return_col = key
				query_model = model
	
	results = {
		'subjects': [],
		'rels': [],
		'rs_results': []
	}
	
	if not query_model:
		results['rs_results'] = find(models.REL_SUBJECT, data)
	else:
		rs_query_prefix = select_where(models.REL_SUBJECT, returning=rs_return_col)
		rs_query = '{} {}'.format(rs_query_prefix, keyify(data, connector=' AND '))
		
		if query_model == models.SUBJECT:
			results['subjects'] = [r[0] for r in find(query_model, {'id': '({})'.format(rs_query)}, returning='orig')]
		else:
			rels = find(query_model, {'id': '({})'.format(rs_query), 'relation': 1})
			rel_results = []
			
			if rels:
				for r in rels:
					subject_ids = (r[1], r[2])
					rel_results.append([r[0] for r in find(models.SUBJECT, {'id': subject_ids}, returning='orig')])
			
			results['rels'] = rel_results
	
	return results


def find_models_through_rr(rr_info, rel_uid_query_map, relation=None):
	query_keys_map = {
		'a_id': [rel_uid_query_map, 'rel_a_uid', models.REL],
		'b_id': [rel_uid_query_map, 'rel_b_uid', models.REL]
	}
	
	data = {}
	
	if relation != None:
		data['relation'] = relation

	rr_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rr_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				rr_return_col = key
				query_model = model
	
	if not query_model:
		return find(models.REL_REL, data)
	
	rr_query_prefix = select_where(models.REL_REL, returning=rr_return_col)
	rr_query = '{} {}'.format(rr_query_prefix, keyify(data, connector=' AND '))
	
	rels = find(query_model, {'id': '({})'.format(rr_query), 'relation': 1})
	results = []
	
	if rels:
		for r in rels:
			subject_ids = (r[1], r[2])
			results.append([r[0] for r in find(models.SUBJECT, {'id': subject_ids}, returning='orig')])
	
	return results


def find_models_through_ssa(ssa_info, actions_uid_query_map, subj_uid_query_map):
	query_keys_map = {
		'a_id': [subj_uid_query_map, 'subj_a_uid', models.SUBJECT],
		'b_id': [subj_uid_query_map, 'subj_b_uid', models.SUBJECT],
		'action_id': [actions_uid_query_map, 'action_uid', models.ACTION]
	}
		
	data = {}
	ssa_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = ssa_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				ssa_return_col = key
				query_model = model
				
	if not query_model:
		return find(models.SUBJECT_SUBJECT_ACTION, data)
	
	ssa_query_prefix = select_where(models.SUBJECT_SUBJECT_ACTION, returning=ssa_return_col)
	ssa_query = '{} {}'.format(ssa_query_prefix, keyify(data, connector=' AND '))

	if query_model == models.SUBJECT:
		return_col = 'orig'
	else:
		return_col = 'verb'
		
	results = find(query_model, {'id': '({})'.format(ssa_query)}, returning=return_col)
	
	return [r[0] for r in results]
	

def find_models_through_rsa(rsa_info, actions_uid_query_map, subj_uid_query_map, rel_uid_query_map, dir=None):
	query_keys_map = {
		'rel_id': [rel_uid_query_map, 'rel_uid', models.REL],
		'subject_id': [subj_uid_query_map, 'subject_uid', models.SUBJECT],
		'action_id': [actions_uid_query_map, 'action_uid', models.ACTION]
	}
	
	data = {}
	
	if dir:
		data['direction'] = dir
		
	rsa_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rsa_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				rsa_return_col = key
				query_model = model
		
	results = {
		'subjects': [],
		'rels': [],
		'rsa_results': []
	}
		
	if not query_model:
		results['rsa_results'] = find(models.REL_SUBJECT_ACTION, data)
	else:
		rsa_query_prefix = select_where(models.REL_SUBJECT_ACTION, returning=rsa_return_col)
		rsa_query = '{} {}'.format(rsa_query_prefix, keyify(data, connector=' AND '))
			
		if query_model == models.SUBJECT:
			results['subjects'] = [r[0] for r in find(query_model, {'id': '({})'.format(rsa_query)}, returning='orig')]
		else:
			rels = find(query_model, {'id': '({})'.format(rsa_query), 'relation': 1})
			rel_results = []
									
			if rels:
				for r in rels:
					subject_ids = (r[1], r[2])
					rel_results.append([r[0] for r in find(models.SUBJECT, {'id': subject_ids}, returning='orig')])
			
			results['rels'] = rel_results
	
	return results


def find_models_through_rra(rra_info, actions_uid_query_map, rel_uid_query_map):
	query_keys_map = {
		'a_id': [rel_uid_query_map, 'rel_a_uid', models.REL],
		'b_id': [rel_uid_query_map, 'rel_b_uid', models.REL],
		'action_id': [actions_uid_query_map, 'action_uid', models.ACTION]
	}
		
	data = {}
	rra_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rra_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				rra_return_col = key
				query_model = model
				
	if not query_model:
		return find(models.REL_REL_ACTION, data)
	
	rra_query_prefix = select_where(models.REL_REL_ACTION, returning=rra_return_col)
	rra_query = '{} {}'.format(rra_query_prefix, keyify(data, connector=' AND '))
	
	rels = find(query_model, {'id': '({})'.format(rra_query), 'relation': 1})
	results = []
	
	if rels:
		for r in rels:
			subject_ids = (r[1], r[2])
			results.append([r[0] for r in find(models.SUBJECT, {'id': subject_ids}, returning='orig')])
		
	return results


def handle_yes_no_query(t):
	q_tree = t[0]
	format, q_content = chop_predicate(q_tree)
	
	if format not in WH_RETRIEVAL_PREDICATE_FORMATS: return False
	
	leading_v = first_of_label(q_content)
	
	if not leading_v: return False
	
	leading_v_label = leading_v.keys()[0]
	
	if leading_v_label == 'V(DO)':
		return fetch_do_yn(q_content)
	
	return None
	
	# if leading_v_label == 'V*':
	# 	modeled_content = format_modeled_content(q_content)
	# else:
	# 	modeled_content = format_modeled_content(q_content[1:])
	
	# return fetch_memory_wh(modeled_content, wh_info, leading_v_label)
	


def chop_relative_q(s):
	print
	

################################
# HELPERS
################################

# Need to format a response into some when/where/with style structure
def chop_pp(pp):
	return {}


def chop_np(np):
	if not valid_np_children(np):
		return None
	
	subject = {'noun': None, 'owner': None, 'det': None}
	adjs, advs = [], []
	
	groups = labeled_leaves(np)
	
	i = 0
	for g in groups:
		label, word = g
		
		if not subject['noun'] and label in nouns:
			subject['noun'] = word
		elif not subject['det'] and label == words.DETERMINER:
			subject['det'] = word
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
		'det': subject['det'],
		'description': {
			'adj': adjs,
			'adv': advs
		}
	}
	
	# if possession exists
	if subject['owner']:
		data['owner'] = corrected_owner(subject['owner'], from_bot_perspec=False)
		data['det'] = None
		
	return data


def chop_wh(wh_tree):
	info = {
		'wh': None,
		'subject': None
	}
	
	if not valid_wh_children(wh_tree):
		return None
	
	if len(wh_tree) == 1:
		info['wh'] = wh_tree[0][0].lower()
	else:
		feaux_chopped_np = {}
		
		for child in wh_tree:
			label = child.label()
			
			if label == phrases.NOUN_PHRASE and not info['subject']:
				info['subject'] = chop_np(child)
			elif label in [words.NOUN_SINGULAR, words.NOUN_PLURAL] and not feaux_chopped_np.get('noun'):
				feaux_chopped_np['noun'] = child[0]
			elif label in [words.WH_PRONOUN, words.WH_DETERMINER, words.POSSESSIVE_WH_PRONOUN] and not info['wh']:
				info['wh'] = child[0].lower()
		
		if not info['subject'] and feaux_chopped_np:
			feaux_chopped_np['description'] = {
				'adj': [g[1] for g in labeled_leaves(wh_tree) if g[0] in adjectives],
				'adv': []
			}
			
			feaux_chopped_np['owner'] = None
			info['subject'] = feaux_chopped_np
	
	if info['wh'] == 'whose':
		info['wh'] = 'who'
	
	return info


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


def strip_trailing_punc(text):
	return text.strip().rstrip('?:!.,;')


def strip_last_branch(t):
	t[0].pop()
	return t


def add_det_prefix(w):
	if w[0] in ['a', 'e', 'i', 'o', 'u']:
		det = 'an'
	else:
		det = 'a'
	
	return '{} {}'.format(det, w)


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


def valid_wh_children(wh_tree):
	label = wh_tree.label()
	
	if label == phrases.WH_ADV_PHRASE:
		valid_child_labels = set([
			words.WH_ADVERB
		])
	elif label == phrases.WH_NOUN_PHRASE:
		valid_child_labels = set([
			words.WH_PRONOUN,
			words.WH_DETERMINER,
			words.POSSESSIVE_WH_PRONOUN,
			phrases.ADJ_PHRASE,
			words.ADJ,
			words.ADJ_COMPARATIVE,
			words.ADJ_SUPERLATIVE,
			words.NOUN_SINGULAR,
			words.NOUN_PLURAL,
			phrases.NOUN_PHRASE
		])
	else:
		error('WH Tree Label ({}) not valid for mem query.'.format(label))
	
	for l in all_nested_labels(wh_tree):
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


def first_of_label(pred_content, label='*'):
	for g in pred_content:
		if isinstance(g, list):
			return first_of_label(g)
		elif isinstance(g, dict) and g.keys() and (g.keys()[0] == label or label == '*'):
			return g
		
	return None


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