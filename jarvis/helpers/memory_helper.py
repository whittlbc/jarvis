import jarvis.helpers.nlp.stanford_parser as sp
from jarvis.helpers.nlp.memory_formats import STORAGE_PREDICATE_FORMATS, WH_RETRIEVAL_PREDICATE_FORMATS, RESTRICTED_LABELS
from jarvis.helpers.nlp.lemmatizer import lemmatizer
from jarvis.helpers.nlp.names import names_map
from jarvis.helpers.helpers import corrected_owner, format_possession, and_join
from nltk.tree import Tree
from nltk import pos_tag
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
	ss_locations = {}
	rs_locations = {}
	rr_locations = {}
	ssas_locations = {}
	ssar_locations = {}
	rsas_locations = {}
	rsar_locations = {}
	rras_locations = {}
	rrar_locations = {}
	
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
			
			elif data.get('action'):
				a = data['action']
				action_uid = uid()
				actions[action_uid] = {'verb': a['v']}
				
				if a.get('subject'):
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
					
				elif a.get('location'):
					if lead_subj_type == 'subj':
						subj_subj_action_uid = uid()
						subj_subj_actions[subj_subj_action_uid] = {
							'subj_a_uid': lead_subj_noun_uid,
							'subj_b_uid': -1,
							'action_uid': action_uid
						}
					else:
						rel_subj_action_uid = uid()
						rel_subj_actions[rel_subj_action_uid] = {
							'rel_uid': lead_subj_rel_uid,
							'subject_uid': -1,
							'action_uid': action_uid,
							'direction': 1
						}
						
					loc = a['location']
					prep = loc['prep']
					loc_subj = loc['subject']
					
					loc_subj_type = 'subj'
					loc_subj_noun_uid = uid()
					subjects[loc_subj_noun_uid] = {'orig': loc_subj['noun']}
					
					if loc_subj['owner']:
						loc_subj_type = 'rel'
						loc_subj_owner_uid = uid()
						subjects[loc_subj_owner_uid] = {'orig': loc_subj['owner']}
						
						loc_subj_rel_uid = uid()
						rels[loc_subj_rel_uid] = {
							'subj_a_uid': loc_subj_owner_uid,
							'subj_b_uid': loc_subj_noun_uid,
							'relation': 1
						}
				
					if lead_subj_type == 'subj' and loc_subj_type == 'subj':  # ssas
						ssas_locations[uid()] = {
							'ssa_uid': subj_subj_action_uid,
							'subject_uid': loc_subj_noun_uid,
							'prep': prep
						}
						
					elif lead_subj_type == 'subj' and loc_subj_type == 'rel':  # ssar
						ssar_locations[uid()] = {
							'ssa_uid': subj_subj_action_uid,
							'rel_uid': loc_subj_rel_uid,
							'prep': prep
						}
						
					elif lead_subj_type == 'rel' and loc_subj_type == 'subj': # rsas
						rsas_locations[uid()] = {
							'rsa_uid': rel_subj_action_uid,
							'subject_uid': loc_subj_noun_uid,
							'prep': prep
						}
						
					else: # rsar
						rsar_locations[uid()] = {
							'rsa_uid': rel_subj_action_uid,
							'rel_uid': loc_subj_rel_uid,
							'prep': prep
						}
		
		else:
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
					else: # V(OWN)
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
					else: # V(OWN)
						order = 1
						
					rel_subjects[rel_subj_uid] = {
						'rel_uid': lead_subj_rel_uid,
						'subject_uid': outer_subj_noun_uid,
						'relation': order
					}
					
				elif lead_subj_type == 'subj' and outer_subj_type == 'rel':
					rel_subj_uid = uid()
					
					if leading_v_label == 'V(BE)':
						order = 0
					
						# If something like "Tyler is my brother", we should also
						# store the parent-child equivalent: "Tyler is a brother"
						rels[uid()] = {
							'subj_a_uid': lead_subj_noun_uid,
							'subj_b_uid': outer_subj_noun_uid,
							'relation': 2
						}
					else: # V(OWN)
						order = -1
						
					rel_subjects[rel_subj_uid] = {
						'rel_uid': outer_subj_rel_uid,
						'subject_uid': lead_subj_noun_uid,
						'relation': order
					}
					
				else: # both are 'rel'
					rel_rel_uid = uid()
					
					if leading_v_label == 'V(BE)':
						order = 0

						# If something like "My friend is my brother", we should also
						# store the parent-child equivalent: "My friend is a brother"
						rel_subjects[uid()] = {
							'rel_uid': lead_subj_rel_uid,
							'subject_uid': outer_subj_noun_uid,
							'relation': 2
						}
					else: # V(OWN)
						order = 1
						
					rel_rels[rel_rel_uid] = {
						'rel_a_uid': lead_subj_rel_uid,
						'rel_b_uid': outer_subj_rel_uid,
						'relation': order
					}
			
			else:
				# LOCATION
				if data.get('location'):
					loc = data['location']
					prep = loc['prep']
					loc_subj = loc['subject']
					
					loc_subj_type = 'subj'
					loc_subj_noun_uid = uid()
					subjects[loc_subj_noun_uid] = {'orig': loc_subj['noun']}
					
					if loc_subj['owner']:
						loc_subj_type = 'rel'
						loc_subj_owner_uid = uid()
						subjects[loc_subj_owner_uid] = {'orig': loc_subj['owner']}
						
						loc_subj_rel_uid = uid()
						rels[loc_subj_rel_uid] = {
							'subj_a_uid': loc_subj_owner_uid,
							'subj_b_uid': loc_subj_noun_uid,
							'relation': 1
						}
					
					if lead_subj_type == 'subj' and loc_subj_type == 'subj':
						ss_locations[uid()] = {
							'subj_a_uid': lead_subj_noun_uid,
							'subj_b_uid': loc_subj_noun_uid,
							'prep': prep
						}
						
					elif lead_subj_type == 'rel' and loc_subj_type == 'subj':
						rs_locations[uid()] = {
							'rel_uid': lead_subj_rel_uid,
							'subject_uid': loc_subj_noun_uid,
							'prep': prep,
							'direction': 1
						}
						
					elif lead_subj_type == 'subj' and loc_subj_type == 'rel':
						rs_locations[uid()] = {
							'rel_uid': loc_subj_rel_uid,
							'subject_uid': lead_subj_noun_uid,
							'prep': prep,
							'direction': -1
						}
						
					else:
						rr_locations[uid()] = {
							'rel_a_uid': lead_subj_rel_uid,
							'rel_b_uid': loc_subj_rel_uid,
							'prep': prep
						}
					
				elif data.get('datetime'):
					# same as location pretty much
					print
					
				else:
					# description
					print
					
	# Subjects
	subj_uid_id_map = upsert_subjects(subjects)
	
	# Rels
	rel_uid_id_map = upsert_rels(rels, subj_uid_id_map)
	rel_subj_uid_id_map = upsert_rel_subjects(rel_subjects, subj_uid_id_map, rel_uid_id_map)
	rel_rel_uid_id_map = upsert_rel_rels(rel_rels, rel_uid_id_map)
	
	# Actions
	actions_uid_id_map = upsert_actions(actions)
	subj_subj_action_uid_id_map = upsert_subj_subj_actions(subj_subj_actions, actions_uid_id_map, subj_uid_id_map)
	rel_subj_action_uid_id_map = upsert_rel_subj_actions(rel_subj_actions, actions_uid_id_map, subj_uid_id_map, rel_uid_id_map)
	rel_rel_action_uid_id_map = upsert_rel_rel_actions(rel_rel_actions, actions_uid_id_map, rel_uid_id_map)
	
	# Locations
	upsert_ss_locations(ss_locations, subj_uid_id_map)
	upsert_rs_locations(rs_locations, subj_uid_id_map, rel_uid_id_map)
	upsert_rr_locations(rr_locations, rel_uid_id_map)
	upsert_ssas_locations(ssas_locations, subj_subj_action_uid_id_map, subj_uid_id_map)
	upsert_ssar_locations(ssar_locations, subj_subj_action_uid_id_map, rel_uid_id_map)
	upsert_rsas_locations(rsas_locations, rel_subj_action_uid_id_map, subj_uid_id_map)
	upsert_rsar_locations(rsar_locations, rel_subj_action_uid_id_map, rel_uid_id_map)
	upsert_rras_locations(rras_locations, rel_rel_action_uid_id_map, subj_uid_id_map)
	upsert_rrar_locations(rrar_locations, rel_rel_action_uid_id_map, rel_uid_id_map)
	
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
	
	upsert_info = {
		'a_id': [subj_uid_id_map, 'subj_a_uid'],
		'b_id': [subj_uid_id_map, 'subj_b_uid'],
		'action_id': [actions_uid_id_map, 'action_uid']
	}
	
	for k, v in subj_subj_actions.items():
		data = {}
		
		for key, uid_info in upsert_info.items():
			m, uid_key = uid_info
			val = v[uid_key]
			
			if val == -1:
				data[key] = -1
			else:
				data[key] = m[val]
		
		id = upsert(models.SUBJECT_SUBJECT_ACTION, data)
		uid_id_map[k] = id
	
	return uid_id_map
	
	
def upsert_rel_subj_actions(rel_subj_actions, actions_uid_id_map, subj_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	upsert_info = {
		'rel_id': [rel_uid_id_map, 'rel_uid'],
		'subject_id': [subj_uid_id_map, 'subject_uid'],
		'action_id': [actions_uid_id_map, 'action_uid'],
	}
	
	for k, v in rel_subj_actions.items():
		data = {'direction': v['direction']}
		
		for key, uid_info in upsert_info.items():
			m, uid_key = uid_info
			val = v[uid_key]
			
			if val == -1:
				data[key] = -1
			else:
				data[key] = m[val]
		
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


def upsert_ss_locations(ss_locations, subj_uid_id_map):
	uid_id_map = {}
	
	for k, v in ss_locations.items():
		data = {
			'a_id': subj_uid_id_map[v['subj_a_uid']],
			'b_id': subj_uid_id_map[v['subj_b_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.SS_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_rs_locations(rs_locations, subj_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rs_locations.items():
		data = {
			'rel_id': rel_uid_id_map[v['rel_uid']],
			'subject_id': subj_uid_id_map[v['subject_uid']],
			'prep': v['prep'],
			'direction': v['direction']
		}
		
		id = upsert(models.RS_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_rr_locations(rr_locations, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rr_locations.items():
		data = {
			'a_id': rel_uid_id_map[v['rel_a_uid']],
			'b_id': rel_uid_id_map[v['rel_b_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.RR_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_ssas_locations(ssas_locations, subj_subj_action_uid_id_map, subj_uid_id_map):
	uid_id_map = {}
	
	for k, v in ssas_locations.items():
		data = {
			'subject_subject_action_id': subj_subj_action_uid_id_map[v['ssa_uid']],
			'subject_id': subj_uid_id_map[v['subject_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.SSAS_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map
	
	
def upsert_ssar_locations(ssar_locations, subj_subj_action_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in ssar_locations.items():
		data = {
			'subject_subject_action_id': subj_subj_action_uid_id_map[v['ssa_uid']],
			'rel_id': rel_uid_id_map[v['rel_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.SSAR_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map

	
def upsert_rsas_locations(rsas_locations, rel_subj_action_uid_id_map, subj_uid_id_map):
	uid_id_map = {}
	
	for k, v in rsas_locations.items():
		data = {
			'rel_subject_action_id': rel_subj_action_uid_id_map[v['rsa_uid']],
			'subject_id': subj_uid_id_map[v['subject_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.RSAS_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map
	
	
def upsert_rsar_locations(rsar_locations, rel_subj_action_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rsar_locations.items():
		data = {
			'rel_subject_action_id': rel_subj_action_uid_id_map[v['rsa_uid']],
			'rel_id': rel_uid_id_map[v['rel_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.RSAR_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_rras_locations(rras_locations, rel_rel_action_uid_id_map, subj_uid_id_map):
	uid_id_map = {}
	
	for k, v in rras_locations.items():
		data = {
			'rel_rel_action_id': rel_rel_action_uid_id_map[v['rra_uid']],
			'subject_id': subj_uid_id_map[v['subject_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.RRAS_LOCATION, data)
		uid_id_map[k] = id
	
	return uid_id_map


def upsert_rrar_locations(rrar_locations, rel_rel_action_uid_id_map, rel_uid_id_map):
	uid_id_map = {}
	
	for k, v in rrar_locations.items():
		data = {
			'rel_rel_action_id': rel_rel_action_uid_id_map[v['rra_uid']],
			'rel_id': rel_uid_id_map[v['rel_uid']],
			'prep': v['prep']
		}
		
		id = upsert(models.RRAR_LOCATION, data)
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
				
			elif key == phrases.NOUN_PHRASE:
				if content.get('action'):
					content['action']['subject'] = val
				else:
					content['subject'] = val
					
			elif key == phrases.PREP_PHRASE:
				prep_data = {'prep': val['prep'], 'subject': val['np']}
				prep_type = val['prep_type'] # 'datetime' or 'location'
				
				if content.get('action'):
					content['action'][prep_type] = prep_data
				else:
					content[prep_type] = prep_data
			
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
				# Check if this tree has any PP children (whether NP or PP)
				pp_children = [c for c in child if has_label(c, phrases.PREP_PHRASE)]
				
				if pp_children:
					error('{} tree cannot have PP\'s for children just yet'.format(label))
				
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
	trailing_words = []
	count = 0
	
	for g in pos_tag(strip_trailing_punc(text).split()):
		word, label = g
		
		if label == words.MODAL or (count == 0 and lemmatize(word.lower(), pos='v') == 'do'):
			word = 'did'
		
		trailing_words.append(word)
		count += 1
		
	text = ' '.join(trailing_words) + '?'
	tree = to_tree(text)
	answer = None
	
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
		
		if leading_v_label == 'V*':
			modeled_content = format_modeled_content(q_content)
			
		elif leading_v_label == 'V(BE)':
			modeled_content = format_modeled_content(q_content[1:])
			
		else:
			modeled_content = format_modeled_content(q_content[0][1:])
		
		return fetch_memory_wh(modeled_content, wh_info, leading_v_label)
		
	elif q_type == 'relative':
		error('q_type "relative" not yet implemented...{}'.format(q_type))
	else:
		error('q_type not valid while handling WH mem query: {}'.format(q_type))


def fetch_wh_do(q_content, wh_info):
	np = first_of_label(q_content, label=phrases.NOUN_PHRASE)
	
	if not np:
		error('WH-DO query has no NP for some reason...{}'.format(tree))
	
	subject = np.values()[0]
	sub_lists = [l for l in q_content if isinstance(l, list)]
	
	if not sub_lists:
		error('WH-DO query has no VP for some reason...{}'.format(tree))
	
	action = {}
	possession = None
	has_v_own = False
	
	for child in sub_lists[0]:  # the first VP
		label, val = child.items()[0]
		
		if label == 'V*' and not action:
			action['v'] = val
		
		elif label == 'V(OWN)':
			has_v_own = True
		
		elif label == phrases.NOUN_PHRASE and action:
			action['subject'] = val
		
		# Not supporting the use of NP's after WH-DO-OWN's yet
		# elif label == phrases.NOUN_PHRASE and has_v_own:
		# 	possession = val
	
	if action:
		action['adj'] = []
		action['adv'] = []

		if wh_info['wh'] in ['when', 'where']:
			handle_method = handle_whadvp_do_action
		else:
			handle_method = handle_whnp_do_action
		
		for s in find_all_subj_eqs(subject):
			result = handle_method(s, action, wh_info)
			
			if result: 
				return result
			
	elif has_v_own:
		if wh_info['wh'] in ['when', 'where']:
			handle_method = handle_whadvp_do_possession
		else:
			handle_method = handle_whnp_do_possession
			
		for s in find_all_subj_eqs(subject):
			result = handle_method(s, possession, wh_info)
			
			if result:
				return result
	
	return None


# Ex: Where do I play? --> in the streets
# ** ONLY FOCUSING ON WHERE QUERIES FOR NOW **
def handle_whadvp_do_action(subject, action, wh_info):
	subjects = {}
	rels = {}
	actions = {}
	subj_subj_actions = {}
	rel_subj_actions = {}
	
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
	
	action_uid = uid()
	actions[action_uid] = {'verb': action['v']}
	
	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
	actions_uid_query_map = action_query_map(actions)
	
	result = []
	
	if lead_subj_type == 'subj':
		# assuming that there's no subject associated with the action...
		# we'll be looking for both ssas_locations and ssar_locations where b_id = -1 in the ssa model
		ssa_uid = uid()
		subj_subj_actions[ssa_uid] = {
			'subj_a_uid': lead_subj_noun_uid,
			'subj_b_uid': -1,
			'action_uid': action_uid
		}
		
		ssa_uid_query_map = ssa_query_map(subj_subj_actions, actions_uid_query_map, subj_uid_query_map)
		
		ssas_loc_info = {
			'ssa_uid': ssa_uid,
			'subject_uid': '*',
			'prep': '*'
		}
		
		ssas_loc_results = find_models_through_ssas_loc(ssas_loc_info, ssa_uid_query_map, subj_uid_query_map)
	
		result += ssas_loc_results
		
		
		
	# else:  # lead_subj_type = 'rel'
	# 	rs_uid_info = {
	# 		'rel_uid': lead_subj_rel_uid,
	# 		'subject_uid': wh_info['wh'],
	# 		'action_uid': action_uid
	# 	}
	#
	# 	rr_uid_info = {
	# 		'rel_a_uid': lead_subj_rel_uid,
	# 		'rel_b_uid': wh_info['wh'],
	# 		'action_uid': action_uid
	# 	}
	#
	# 	rsa_results = find_models_through_rsa(
	# 		rs_uid_info,
	# 		actions_uid_query_map,
	# 		subj_uid_query_map,
	# 		rel_uid_query_map,
	# 		dir=1
	# 	)
	#
	# 	rra_results = find_models_through_rra(
	# 		rr_uid_info,
	# 		actions_uid_query_map,
	# 		rel_uid_query_map
	# 	)
	#
	# 	result += [corrected_owner(r) for r in rsa_results['subjects']]
	#
	# 	for group in rra_results:
	# 		result.append(format_possession([corrected_owner(g) for g in group]))
	
	return and_join(result)


# Ex: What do I play? --> basketball
# Use subject as leading subject and assume that action doesn't have a 'subject' property
# TODO: Still need to figure out how to deal with possessive wh_info's
def handle_whnp_do_action(subject, action, wh_info):
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
			'relation': 1
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


def handle_whadvp_do_possession(subject, possession, wh_info):
	# TODO: errthang
	return None


# Ex: What do I have?
# TODO: Still need to figure out how to deal with possessive wh_info's
def handle_whnp_do_possession(subject, possession, wh_info):
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
		
	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
	
	result = []

	if lead_subj_type == 'subj':
		r_uid_info = {
			'subj_a_uid': lead_subj_noun_uid,
			'subj_b_uid': wh_info['wh'],
		}
		
		rs_uid_info = {
			'rel_uid': wh_info['wh'],
			'subject_uid': lead_subj_noun_uid
		}
		
		r_results = find_models_through_r(
			r_uid_info,
			subj_uid_query_map,
			relation=1
		)
		
		rs_results = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=-1
		)
		
		r_results = [corrected_owner(r) for r in r_results]
		result += [add_det_prefix(w) for w in r_results]
		
		for group in rs_results['rels']:
			result.append(format_possession([corrected_owner(g) for g in group]))
	
	else:  # lead_subj_type == 'rel'
		rs_uid_info = {
			'rel_uid': lead_subj_rel_uid,
			'subject_uid': wh_info['wh']
		}
		
		rr_uid_info = {
			'rel_a_uid': lead_subj_rel_uid,
			'rel_b_uid': wh_info['wh']
		}
		
		rs_results = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=1
		)
		
		rr_results = find_models_through_rr(
			rr_uid_info,
			rel_uid_query_map,
			relation=1
		)
		
		rs_subj_results = [corrected_owner(r) for r in rs_results['subjects']]
		result += [add_det_prefix(w) for w in rs_subj_results]
		
		for group in rr_results:
			result.append(format_possession([corrected_owner(g) for g in group]))
		
	return and_join(result)


def fetch_do_yn(q_content):
	np = first_of_label(q_content, label=phrases.NOUN_PHRASE)
	
	if not np:
		error('DO query has no NP for some reason...{}'.format(tree))
	
	subject = np.values()[0]
	sub_lists = [l for l in q_content if isinstance(l, list)]
	
	if not sub_lists:
		error('DO query has no VP for some reason...{}'.format(tree))
	
	action = {}
	possession = None
	has_v_own = False
	
	for child in sub_lists[0]:  # the first VP
		label, val = child.items()[0]
		
		if label == 'V*':	# 12/24 - changed from `if label == 'V*' and not subject` to fix issue with "Do I play?" query.
			action['v'] = val
			
		elif label == 'V(OWN)':
			has_v_own = True
			
		elif label == phrases.NOUN_PHRASE and action:
			action['subject'] = val
			
		elif label == phrases.NOUN_PHRASE and has_v_own:
			possession = val
	
	if action:
		action['adj'] = []
		action['adv'] = []
		
		for s in find_all_subj_eqs(subject):
			result = handle_do_yn_action(s, action)
			
			if result == 'Yes':
				return result
	
	elif possession:
		for s in find_all_subj_eqs(subject):
			result = handle_do_yn_possession(s, possession)
			
			if result == 'Yes':
				return result
	
	return 'No'


# Is Tyler my brother?
def fetch_is_yn(q_content):
	# Strip out NP's from content
	subjects = [t.values()[0] for t in q_content if t.keys()[0] == phrases.NOUN_PHRASE]
	
	# Ensure 2 subjects exist since we're checking for a comparison.
	if len(subjects) != 2:
		error('Is-YN query doesn\'t have 2 NP instances for comparison...{}'.format(q_content))
	
	former, latter = subjects
	
	equiv_subjs = [s for s in find_all_subj_eqs(former)]
	
	if latter['det'] and latter['det'].lower() in ['a', 'an']: # relation=2
		parents = []
		for s in equiv_subjs:
			parents += find_parents_for_child(s)
		
		equiv_subjs = parents
		
	else: # relation=0
		equiv_subjs = [s for s in equiv_subjs if s != former]
			
	latter_match_info = [None, latter['noun'].lower()]
	
	if latter['owner']:
		latter_match_info[0] = latter['owner'].lower()
	
	for s in equiv_subjs:
		s_info = [None, s['noun'].lower()]
		
		if s['owner']:
			s_info[0] = s['owner'].lower()
		
		if s_info == latter_match_info:
			return 'Yes'
		
	return 'No'


def find_parents_for_child(subject):
	parents = []
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
		
	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
	
	if lead_subj_type == 'subj':
		r_uid_info = {
			'subj_a_uid': lead_subj_noun_uid,
			'subj_b_uid': 'wh*',
		}
		
		results = find_models_through_r(
			r_uid_info,
			subj_uid_query_map,
			relation=2
		)
	else:
		rs_uid_info = {
			'rel_uid': lead_subj_rel_uid,
			'subject_uid': 'wh*'
		}
		
		results = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=2
		)['subjects']
		
	for s in results:
		parents.append({
			'owner': None,
			'noun': s,
			'det': None,
			'description': {'adv': [], 'adj': []}
		})
		
	return parents
			

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
				'det': None,
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
					'det': None,
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
					'det': None,
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
				'det': None,
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
	
	if action_subj and action_subj['noun'].lower() not in ['anything', 'something']:
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


# Determine if subject owns the possession
def handle_do_yn_possession(subject, possession):
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
		
	poss_subj_type = None
	
	if possession['noun'].lower() not in ['anything', 'something']:
		poss_subj_type = 'subj'
		poss_subj_noun_uid = uid()
		subjects[poss_subj_noun_uid] = {'orig': possession['noun']}
		
		if possession['owner']:
			poss_subj_type = 'rel'
			poss_subj_owner_uid = uid()
			subjects[poss_subj_owner_uid] = {'orig': possession['owner']}
			
			poss_subj_rel_uid = uid()
			rels[poss_subj_rel_uid] = {
				'subj_a_uid': poss_subj_owner_uid,
				'subj_b_uid': poss_subj_noun_uid,
				'relation': 1
			}

	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
	
	result = []
	
	if lead_subj_type == 'subj' and poss_subj_type == 'subj':
		r_uid_info = {
			'subj_a_uid': lead_subj_noun_uid,
			'subj_b_uid': poss_subj_noun_uid,
		}
		
		result = find_models_through_r(
			r_uid_info,
			subj_uid_query_map,
			relation=1
		)
		
	elif lead_subj_type == 'subj' and poss_subj_type == 'rel':
		rs_uid_info = {
			'rel_uid': poss_subj_rel_uid,
			'subject_uid': lead_subj_noun_uid
		}
		
		result = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=-1
		)['rs_results']
				
	elif lead_subj_type == 'rel' and poss_subj_type == 'subj':
		rs_uid_info = {
			'rel_uid': lead_subj_noun_uid,
			'subject_uid': poss_subj_noun_uid
		}
		
		result = find_models_through_rs(
			rs_uid_info,
			subj_uid_query_map,
			rel_uid_query_map,
			relation=1
		)['rs_results']
		
	elif lead_subj_type == 'rel' and poss_subj_type == 'rel':
		rr_uid_info = {
			'rel_a_uid': lead_subj_rel_uid,
			'rel_b_uid': poss_subj_rel_uid
		}
		
		result = find_models_through_rr(
			rr_uid_info,
			rel_uid_query_map,
			relation=1
		)
	else: # possession['noun'] == 'anything'
		if lead_subj_type == 'subj':
			r_uid_info = {
				'subj_a_uid': lead_subj_noun_uid,
				'subj_b_uid': '*',
			}
			
			rs_uid_info = {
				'rel_uid': '*',
				'subject_uid': lead_subj_noun_uid
			}
			
			result += find_models_through_r(
				r_uid_info,
				subj_uid_query_map,
				relation=1
			)

			result += find_models_through_rs(
				rs_uid_info,
				subj_uid_query_map,
				rel_uid_query_map,
				relation=-1
			)['rs_results']
		
		else: # lead_subj_type == 'rel'
			rs_uid_info = {
				'rel_uid': lead_subj_rel_uid,
				'subject_uid': '*'
			}
			
			rr_uid_info = {
				'rel_a_uid': lead_subj_rel_uid,
				'rel_b_uid': '*'
			}
			
			result += find_models_through_rs(
				rs_uid_info,
				subj_uid_query_map,
				rel_uid_query_map,
				relation=1
			)['rs_results']
			
			result += find_models_through_rr(
				rr_uid_info,
				rel_uid_query_map,
				relation=1
			)
			
	if result:
		return 'Yes'
	else:
		return 'No'


def fetch_memory_wh(modeled_content, wh_info, leading_v_label):
	subjects = {}
	rels = {}
	rel_subjects = {}
	rel_rels = {}
	actions = {}
	subj_subj_actions = {}
	rel_subj_actions = {}
	rel_rel_actions = {}
	ss_locations = {}
	rs_locations = {}
	rr_locations = {}
	ssas_locations = {}
	rsas_locations = {}
	rras_locations = {}
	ssar_locations = {}
	rsar_locations = {}
	rrar_locations = {}
	
	inner_subj_type = None
	loc_subj_type = None
		
	for data in modeled_content:
		if leading_v_label == 'V*':  # ACTION
			a = data['action']
			action_uid = uid()
			actions[action_uid] = {'verb': a['v']}
			action_subj_type = None
			loc_subj_type = None
			
			if a.get('subject'):
				action_subj = a['subject']
			
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
			
			elif a.get('location'):
				# First need to populate the action-based models
				ssa_uid = uid()
				subj_subj_actions[ssa_uid] = {
					'subj_a_uid': '*',
					'subj_b_uid': '*',
					'action_uid': action_uid
				}
				
				rsa_forward_uid = uid()
				rel_subj_actions[rsa_forward_uid] = {
					'rel_uid': '*',
					'subject_uid': '*',
					'action_uid': action_uid,
					'direction': 1
				}
				
				rsa_backward_uid = uid()
				rel_subj_actions[rsa_backward_uid] = {
					'rel_uid': '*',
					'subject_uid': '*',
					'action_uid': action_uid,
					'direction': -1
				}
			
				rra_uid = uid()
				rel_rel_actions[rra_uid] = {
					'rel_a_uid': '*',
					'rel_b_uid': '*',
					'action_uid': action_uid
				}
					
				loc = a['location']
				prep = loc['prep']
				loc_subj = loc['subject']
				
				loc_subj_type = 'subj'
				loc_subj_noun_uid = uid()
				subjects[loc_subj_noun_uid] = {'orig': loc_subj['noun']}
				
				if loc_subj['owner']:
					loc_subj_type = 'rel'
					loc_subj_owner_uid = uid()
					subjects[loc_subj_owner_uid] = {'orig': loc_subj['owner']}
					
					loc_subj_rel_uid = uid()
					rels[loc_subj_rel_uid] = {
						'subj_a_uid': loc_subj_owner_uid,
						'subj_b_uid': loc_subj_noun_uid,
						'relation': 1
					}
								
				if loc_subj_type == 'subj':
					ssas_locations[uid()] = {
						'ssa_uid': ssa_uid,
						'subject_uid': loc_subj_noun_uid,
						'prep': prep,
					}
					
					rsas_locations[uid()] = {
						'rsa_uid': rsa_forward_uid,
						'subject_uid': loc_subj_noun_uid,
						'prep': prep
					}
					
					rsas_locations[uid()] = {
						'rsa_uid': rsa_backward_uid,
						'subject_uid': loc_subj_noun_uid,
						'prep': prep
					}
					
					rras_locations[uid()] = {
						'rra_uid': rra_uid,
						'subject_uid': loc_subj_noun_uid,
						'prep': prep,
					}
				
				else:
					ssar_locations[uid()] = {
						'ssa_uid': ssa_uid,
						'rel_uid': loc_subj_rel_uid,
						'prep': prep,
					}
					
					rsar_locations[uid()] = {
						'rsa_uid': rsa_forward_uid,
						'rel_uid': loc_subj_rel_uid,
						'prep': prep
					}
					
					rsar_locations[uid()] = {
						'rsa_uid': rsa_backward_uid,
						'rel_uid': loc_subj_rel_uid,
						'prep': prep
					}
					
					rrar_locations[uid()] = {
						'rra_uid': rra_uid,
						'rel_uid': loc_subj_rel_uid,
						'prep': prep,
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
					
			elif data.get('location'):
				loc = data['location']
				prep = loc['prep']
				loc_subj = loc['subject']
				
				loc_subj_type = 'subj'
				loc_subj_noun_uid = uid()
				subjects[loc_subj_noun_uid] = {'orig': loc_subj['noun']}
				
				if loc_subj['owner']:
					loc_subj_type = 'rel'
					loc_subj_owner_uid = uid()
					subjects[loc_subj_owner_uid] = {'orig': loc_subj['owner']}
					
					loc_subj_rel_uid = uid()
					rels[loc_subj_rel_uid] = {
						'subj_a_uid': loc_subj_owner_uid,
						'subj_b_uid': loc_subj_noun_uid,
						'relation': 1
					}
				
				if loc_subj_type == 'subj':
					ss_locations[uid()] = {
						'subj_a_uid': wh_info['wh'],
						'subj_b_uid': loc_subj_noun_uid,
						'prep': prep
					}
					
					rs_locations[uid()] = {
						'rel_uid': wh_info['wh'],
						'subject_uid': loc_subj_noun_uid,
						'prep': prep,
						'direction': 1
					}
					
				else:
					rs_locations[uid()] = {
						'rel_uid': loc_subj_rel_uid,
						'subject_uid': wh_info['wh'],
						'prep': prep,
						'direction': -1
					}
				
					rr_locations[uid()] = {
						'rel_a_uid': wh_info['wh'],
						'rel_b_uid': loc_subj_rel_uid,
						'prep': prep
					}
	
	result = []

	subj_uid_query_map = subject_query_map(subjects)
	rel_uid_query_map = rel_query_map(rels, subj_uid_query_map)
			
	if actions:
		actions_uid_query_map = action_query_map(actions)
		
		if action_subj_type == 'subj':  # Ex: Who plays basketball?
			
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
				
		else:
			ssa_uid_query_map = ssa_query_map(subj_subj_actions, actions_uid_query_map, subj_uid_query_map)
			rsa_uid_query_map = rsa_query_map(rel_subj_actions, actions_uid_query_map, subj_uid_query_map, rel_uid_query_map)
			rra_uid_query_map = rra_query_map(rel_rel_actions, actions_uid_query_map, rel_uid_query_map)

			if loc_subj_type == 'subj':
				ssas_loc_results = find_models_through_ssas_loc(
					ssas_locations.values()[0],
					ssa_uid_query_map,
					subj_uid_query_map,
					return_pos='a'
				)
				
				rsas_loc_rel_results = find_models_through_rsas_loc(
					[r for r in rsas_locations.values() if rel_subj_actions[r['rsa_uid']]['direction'] == 1][0],
					rsa_uid_query_map,
					subj_uid_query_map,
					return_model=models.REL
				)

				rsas_loc_subj_results = find_models_through_rsas_loc(
					[r for r in rsas_locations.values() if rel_subj_actions[r['rsa_uid']]['direction'] == -1][0],
					rsa_uid_query_map,
					subj_uid_query_map,
					return_model=models.SUBJECT
				)
				
				rras_loc_results = find_models_through_rras_loc(
					rras_locations.values()[0],
					rra_uid_query_map,
					subj_uid_query_map,
					return_pos='a'
				)
				
				result += [corrected_owner(r) for r in ssas_loc_results]
			
				for group in rsas_loc_rel_results:
					result.append(format_possession([corrected_owner(g) for g in group]))
			
				result += [corrected_owner(r) for r in rsas_loc_subj_results]
			
				for group in rras_loc_results:
					result.append(format_possession([corrected_owner(g) for g in group]))
				
			elif loc_subj_type == 'rel':
				ssar_loc_results = find_models_through_ssar_loc(
					ssar_locations.values()[0],
					ssa_uid_query_map,
					rel_uid_query_map,
					return_pos='a'
				)
				
				rsar_loc_rel_results = find_models_through_rsar_loc(
					[r for r in rsas_locations.values() if rel_subj_actions[r['rsa_uid']]['direction'] == 1][0],
					rsa_uid_query_map,
					rel_uid_query_map,
					return_model=models.REL
				)
				
				rsar_loc_subj_results = find_models_through_rsar_loc(
					[r for r in rsas_locations.values() if rel_subj_actions[r['rsa_uid']]['direction'] == -1][0],
					rsa_uid_query_map,
					rel_uid_query_map,
					return_model=models.SUBJECT
				)

				rrar_loc_results = find_models_through_rrar_loc(
					rrar_locations.values()[0],
					rra_uid_query_map,
					rel_uid_query_map,
					return_pos='a'
				)
				
				result += [corrected_owner(r) for r in ssar_loc_results]
				
				for group in rsar_loc_rel_results:
					result.append(format_possession([corrected_owner(g) for g in group]))
				
				result += [corrected_owner(r) for r in rsar_loc_subj_results]
				
				for group in rrar_loc_results:
					result.append(format_possession([corrected_owner(g) for g in group]))
				
			else:
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
						'subj_a_uid': wh_info['wh'],
						'subj_b_uid': inner_subj_noun_uid,
						'relation': 2,
						'add_det': False
					},
					{
						'subj_a_uid': inner_subj_noun_uid,
						'subj_b_uid': wh_info['wh'],
						'relation': 2,
						'add_det': True
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
						for r in r_result:
							formatted_r = corrected_owner(r)
							
							if info['add_det']:
								formatted_r = add_det_prefix(formatted_r)
							
							r_results_pc.append(formatted_r)
				
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
					result = r_results_pc
			
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
						'relation': 2,
						'add_det': True
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
						rs_results_eq += [corrected_owner(r) for r in rs_result['subjects']]
					elif info['relation'] == 2:
						for r in rs_result['subjects']:
							formatted_r = corrected_owner(r)
							
							if info['add_det']:
								formatted_r = add_det_prefix(formatted_r)
							
							rs_results_pc.append(formatted_r)
				
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
					result = rs_results_pc
					
			else:
				# Handle location-related query
				if loc_subj_type == 'subj':
					ss_loc_results = find_models_through_ss_loc(
						ss_locations.values()[0],
						subj_uid_query_map
					)
					
					rs_loc_results = find_models_through_rs_loc(
						rs_locations.values()[0],
						subj_uid_query_map,
						rel_uid_query_map,
						direction=1
					)
					
					result += [corrected_owner(r) for r in ss_loc_results]
									
					for group in rs_loc_results['rels']:
						result.append(format_possession([corrected_owner(g) for g in group]))

				elif loc_subj_type == 'rel':
					rs_loc_results = find_models_through_rs_loc(
						rs_locations.values()[0],
						subj_uid_query_map,
						rel_uid_query_map,
						direction=-1
					)
					
					rr_loc_results = find_models_through_rr_loc(
						rr_locations.values()[0],
						rel_uid_query_map
					)
					
					result += [corrected_owner(r) for r in rs_loc_results['subjects']]

					for group in rr_loc_results:
						result.append(format_possession([corrected_owner(g) for g in group]))
		
		elif leading_v_label == 'V(OWN)':
			if inner_subj_type == 'subj':
				r_uid_info = {
					'subj_a_uid': wh_info['wh'],
					'subj_b_uid': inner_subj_noun_uid,
				}
				
				rs_uid_info = {
					'rel_uid': wh_info['wh'],
					'subject_uid': inner_subj_noun_uid
				}

				r_results = find_models_through_r(
					r_uid_info,
					subj_uid_query_map,
					relation=1
				)
								
				rs_results = find_models_through_rs(
					rs_uid_info,
					subj_uid_query_map,
					rel_uid_query_map,
					relation=1
				)
				
				result += [corrected_owner(r) for r in r_results]
				
				for group in rs_results['rels']:
					result.append(format_possession([corrected_owner(g) for g in group]))
			
			elif inner_subj_type == 'rel':
				rr_uid_info = {
					'rel_a_uid': wh_info['wh'],
					'rel_b_uid': inner_subj_rel_uid,
					'relation': 1
				}

				rs_uid_info = {
					'rel_uid': inner_subj_rel_uid,
					'subject_uid': wh_info['wh'],
					'relation': -1
				}
				
				rr_results = find_models_through_rr(
					rr_uid_info,
					rel_uid_query_map,
					relation=1
				)
				
				rs_results = find_models_through_rs(
					rs_uid_info,
					subj_uid_query_map,
					rel_uid_query_map,
					relation=-1
				)
										
				for group in rr_results:
					result.append(format_possession([corrected_owner(g) for g in group]))
					
				result += [corrected_owner(r) for r in rs_results['subjects']]
	
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


def ssa_query_map(subj_subj_actions, actions_uid_query_map, subj_uid_query_map):
	uid_query_map = {}
	query = select_where(models.SUBJECT_SUBJECT_ACTION, returning='id')
	
	query_keys_map = {
		'a_id': [subj_uid_query_map, 'subj_a_uid'],
		'b_id': [subj_uid_query_map, 'subj_b_uid'],
		'action_id': [actions_uid_query_map, 'action_uid']
	}
	
	for k, v in subj_subj_actions.items():
		data = {}
		
		for key, info in query_keys_map.items():
			m, uid = info
			val = v[uid]
			
			if val == -1:
				data[key] = -1
			elif m.get(val):
				data[key] = '({})'.format(m[val])
		
		if data:
			uid_query_map[k] = '{} {}'.format(query, keyify(data, connector=' AND '))

	return uid_query_map


def rsa_query_map(rel_subj_actions, actions_uid_query_map, subj_uid_query_map, rel_uid_query_map):
	uid_query_map = {}
	query = select_where(models.REL_SUBJECT_ACTION, returning='id')
	
	query_keys_map = {
		'rel_id': [rel_uid_query_map, 'rel_uid'],
		'subject_id': [subj_uid_query_map, 'subject_uid'],
		'action_id': [actions_uid_query_map, 'action_uid']
	}
	
	for k, v in rel_subj_actions.items():
		data = {}
		
		if v.get('direction'):
			data['direction'] = v['direction']
		
		for key, info in query_keys_map.items():
			m, uid = info
			val = v[uid]
			
			if m.get(val):
				data[key] = '({})'.format(m[val])
				
		if data:
			uid_query_map[k] = '{} {}'.format(query, keyify(data, connector=' AND '))
	
	return uid_query_map
	
	
def rra_query_map(rel_rel_actions, actions_uid_query_map, rel_uid_query_map):
	uid_query_map = {}
	query = select_where(models.REL_REL_ACTION, returning='id')
	
	query_keys_map = {
		'a_id': [rel_uid_query_map, 'rel_a_uid'],
		'b_id': [rel_uid_query_map, 'rel_b_uid'],
		'action_id': [actions_uid_query_map, 'action_uid']
	}
	
	for k, v in rel_rel_actions.items():
		data = {}
		
		for key, info in query_keys_map.items():
			m, uid = info
			val = v[uid]
			
			if m.get(val):
				data[key] = '({})'.format(m[val])
		
		if data:
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


def find_models_through_ss_loc(ss_loc_info, subj_uid_query_map):
	query_keys_map = {
		'a_id': [subj_uid_query_map, 'subj_a_uid', models.SUBJECT],
		'b_id': [subj_uid_query_map, 'subj_b_uid', models.SUBJECT]
	}
	
	data = {'prep': ss_loc_info['prep']}
	ss_loc_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = ss_loc_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				ss_loc_return_col = key
				query_model = model
	
	if not query_model:
		return find(models.SS_LOCATION, data)
	
	ss_loc_query_prefix = select_where(models.SS_LOCATION, returning=ss_loc_return_col)
	ss_loc_query = '{} {}'.format(ss_loc_query_prefix, keyify(data, connector=' AND '))
	
	results = find(query_model, {'id': '({})'.format(ss_loc_query)}, returning='orig')
	
	return [r[0] for r in results]


def find_models_through_rs_loc(rs_loc_info, subj_uid_query_map, rel_uid_query_map, direction=None):
	query_keys_map = {
		'rel_id': [rel_uid_query_map, 'rel_uid', models.REL],
		'subject_id': [subj_uid_query_map, 'subject_uid', models.SUBJECT]
	}
	
	data = {'prep': rs_loc_info['prep']}
	
	if direction != None:
		data['direction'] = direction
	
	rs_loc_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rs_loc_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				rs_loc_return_col = key
				query_model = model
	
	results = {
		'subjects': [],
		'rels': [],
		'rs_loc_results': []
	}
	
	if not query_model:
		results['rs_loc_results'] = find(models.RS_LOCATION, data)
	else:
		rs_loc_query_prefix = select_where(models.RS_LOCATION, returning=rs_loc_return_col)
		rs_loc_query = '{} {}'.format(rs_loc_query_prefix, keyify(data, connector=' AND '))
		
		if query_model == models.SUBJECT:
			results['subjects'] = [r[0] for r in find(query_model, {'id': '({})'.format(rs_loc_query)}, returning='orig')]
		else:
			rels = find(query_model, {'id': '({})'.format(rs_loc_query), 'relation': 1})
			rel_results = []
			
			if rels:
				for r in rels:
					subject_ids = (r[1], r[2])
					rel_results.append([r[0] for r in find(models.SUBJECT, {'id': subject_ids}, returning='orig')])
			
			results['rels'] = rel_results
	
	return results


def find_models_through_rr_loc(rr_loc_info, rel_uid_query_map):
	query_keys_map = {
		'a_id': [rel_uid_query_map, 'rel_a_uid', models.REL],
		'b_id': [rel_uid_query_map, 'rel_b_uid', models.REL]
	}
	
	data = {'prep': rr_loc_info['prep']}
	rr_loc_return_col = '*'
	query_model = None
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rr_loc_info[uid]
		mini_query = m.get(val)
		
		if mini_query:
			data[key] = '({})'.format(mini_query)
		else:
			if val != '*':
				rr_loc_return_col = key
				query_model = model
	
	if not query_model:
		return find(models.RR_LOCATION, data)
	
	rr_loc_query_prefix = select_where(models.RR_LOCATION, returning=rr_loc_return_col)
	rr_loc_query = '{} {}'.format(rr_loc_query_prefix, keyify(data, connector=' AND '))
	
	rels = find(query_model, {'id': '({})'.format(rr_loc_query), 'relation': 1})
	results = []
	
	if rels:
		for r in rels:
			subject_ids = (r[1], r[2])
			results.append([r[0] for r in find(models.SUBJECT, {'id': subject_ids}, returning='orig')])
	
	return results


def find_models_through_ssas_loc(ssas_loc_info, ssa_uid_query_map, subj_uid_query_map, return_pos=None):
	query_keys_map = {
		'subject_subject_action_id': [ssa_uid_query_map, 'ssa_uid', models.SUBJECT_SUBJECT_ACTION],
		'subject_id': [subj_uid_query_map, 'subject_uid', models.SUBJECT]
	}
	
	data = {}
	prep = ssas_loc_info['prep']
	
	if prep and prep != '*':
		data['prep'] = prep
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = ssas_loc_info[uid]
		
		if m.get(val):
			data[key] = '({})'.format(m[val])
	
	ssas_location_results = find(models.SSAS_LOCATION, data)
	
	results = []
	if ssas_location_results:
		if ssas_loc_info['subject_uid'] == '*':
			for result in ssas_location_results:
				subject = find(models.SUBJECT, {'id': result[2]}, returning='orig')[0][0]
				results.append(['{} the {}'.format(result[3], subject)])
		else:
			for result in ssas_location_results:
				ssa_id = result[1]
				ssa_inner_query_prefix = select_where(models.SUBJECT_SUBJECT_ACTION, returning='{}_id'.format(return_pos))
				ssa_inner_query = '{} {}'.format(ssa_inner_query_prefix, keyify({'id': ssa_id}))
				results += find(models.SUBJECT, {'id': '({})'.format(ssa_inner_query)}, returning='orig')
	
	return [r[0] for r in results]


def find_models_through_rsas_loc(rsas_loc_info, rsa_uid_query_map, subj_uid_query_map, return_model=None):
	query_keys_map = {
		'rel_subject_action_id': [rsa_uid_query_map, 'rsa_uid', models.REL_SUBJECT_ACTION],
		'subject_id': [subj_uid_query_map, 'subject_uid', models.SUBJECT]
	}
	
	data = {'prep': rsas_loc_info['prep']}
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rsas_loc_info[uid]
		
		if m.get(val):
			data[key] = '({})'.format(m[val])
	
	rsas_location_results = find(models.RSAS_LOCATION, data)
	
	results = []
	if rsas_location_results:
		for result in rsas_location_results:
			rsa_id = result[1]
			
			if return_model == models.REL:
				rel_id = find(models.REL_SUBJECT_ACTION, {'id': rsa_id}, returning='rel_id')[0][0]
				rel = find(models.REL, {'id': rel_id})
				
				subj_a_id = rel[0][1]
				subj_b_id = rel[0][2]
				
				subjects = find(models.SUBJECT, {'id': [subj_a_id, subj_b_id]}, returning='orig')
				results.append([subjects[0][0], subjects[1][0]])
			
			elif return_model == models.SUBJECT:
				subject_id = find(models.REL_SUBJECT_ACTION, {'id': rsa_id}, returning='subject_id')[0][0]
				subject = find(models.SUBJECT, {'id': subject_id}, returning='orig')
				
				results += subject[0][0]
			
			else:
				error('Return model invalid: {}'.format(return_model))
	
	return results

	
def find_models_through_rras_loc(rras_loc_info, rra_uid_query_map, subj_uid_query_map, return_pos=None):
	query_keys_map = {
		'rel_rel_action_id': [rra_uid_query_map, 'rra_uid', models.REL_REL_ACTION],
		'subject_id': [subj_uid_query_map, 'subject_uid', models.SUBJECT]
	}
	
	data = {'prep': rras_loc_info['prep']}
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rras_loc_info[uid]
		
		if m.get(val):
			data[key] = '({})'.format(m[val])
	
	rras_location_results = find(models.RRAS_LOCATION, data)
	
	results = []
	if rras_location_results:
		for result in rras_location_results:
			rra_id = result[1]
			rel_id = find(models.REL_REL_ACTION, {'id': rra_id}, returning='{}_id'.format(return_pos))[0][0]
			rel = find(models.REL, {'id': rel_id})
			
			subj_a_id = rel[0][1]
			subj_b_id = rel[0][2]
			
			subjects = find(models.SUBJECT, {'id': [subj_a_id, subj_b_id]}, returning='orig')
			results.append([subjects[0][0], subjects[1][0]])
	
	return results


def find_models_through_ssar_loc(ssar_loc_info, ssa_uid_query_map, rel_uid_query_map, return_pos=None):
	query_keys_map = {
		'subject_subject_action_id': [ssa_uid_query_map, 'ssa_uid', models.SUBJECT_SUBJECT_ACTION],
		'rel_id': [rel_uid_query_map, 'rel_uid', models.REL]
	}
	
	data = {'prep': ssas_loc_info['prep']}
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = ssar_loc_info[uid]
		
		if m.get(val):
			data[key] = '({})'.format(m[val])
	
	ssar_location_results = find(models.SSAR_LOCATION, data)
	
	results = []
	if ssar_location_results:
		for result in ssar_location_results:
			ssa_id = result[1]
			
			ssa_inner_query_prefix = select_where(models.SUBJECT_SUBJECT_ACTION, returning='{}_id'.format(return_pos))
			ssa_inner_query = '{} {}'.format(ssa_inner_query_prefix, keyify({'id': ssa_id}))
			
			results += find(models.SUBJECT, {'id': '({})'.format(ssa_inner_query)}, returning='orig')
	
	return [r[0] for r in results]


def find_models_through_rsar_loc(rsar_loc_info, rsa_uid_query_map, rel_uid_query_map, return_model=None):
	query_keys_map = {
		'rel_subject_action_id': [rsa_uid_query_map, 'rsa_uid', models.REL_SUBJECT_ACTION],
		'rel_id': [rel_uid_query_map, 'rel_uid', models.REL]
	}
	
	data = {'prep': rsar_loc_info['prep']}
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rsar_loc_info[uid]
		
		if m.get(val):
			data[key] = '({})'.format(m[val])
	
	rsar_location_results = find(models.RSAR_LOCATION, data)
	
	results = []
	if rsar_location_results:
		for result in rsar_location_results:
			rsa_id = result[1]
			
			if return_model == models.REL:
				rel_id = find(models.REL_SUBJECT_ACTION, {'id': rsa_id}, returning='rel_id')[0][0]
				rel = find(models.REL, {'id': rel_id})
				
				subj_a_id = rel[0][1]
				subj_b_id = rel[0][2]
				
				subjects = find(models.SUBJECT, {'id': [subj_a_id, subj_b_id]}, returning='orig')
				results.append([subjects[0][0], subjects[1][0]])
			
			elif return_model == models.SUBJECT:
				subject_id = find(models.REL_SUBJECT_ACTION, {'id': rsa_id}, returning='subject_id')[0][0]
				subject = find(models.SUBJECT, {'id': subject_id}, returning='orig')
				
				results += subject[0][0]
			
			else:
				error('Return model invalid: {}'.format(return_model))
	
	return results


def find_models_through_rrar_loc(rrar_loc_info, rra_uid_query_map, rel_uid_query_map, return_pos=None):
	query_keys_map = {
		'rel_rel_action_id': [rra_uid_query_map, 'rra_uid', models.REL_REL_ACTION],
		'rel_id': [rel_uid_query_map, 'rel_uid', models.REL]
	}
	
	data = {'prep': rrar_loc_info['prep']}
	
	for key, info in query_keys_map.items():
		m, uid, model = info
		val = rrar_loc_info[uid]
		
		if m.get(val):
			data[key] = '({})'.format(m[val])
	
	rrar_location_results = find(models.RRAR_LOCATION, data)
	
	results = []
	if rrar_location_results:
		for result in rrar_location_results:
			rra_id = result[1]
			rel_id = find(models.REL_REL_ACTION, {'id': rra_id}, returning='{}_id'.format(return_pos))[0][0]
			rel = find(models.REL, {'id': rel_id})
			
			subj_a_id = rel[0][1]
			subj_b_id = rel[0][2]
			
			subjects = find(models.SUBJECT, {'id': [subj_a_id, subj_b_id]}, returning='orig')
			results.append([subjects[0][0], subjects[1][0]])
	
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
	elif leading_v_label == 'V(BE)':
		return fetch_is_yn(q_content)
	
	return None


def chop_relative_q(s):
	print
	

################################
# HELPERS
################################

def is_datetime(noun):
	return False


# def is_location(noun):
# 	return True


def chop_pp(pp):
	prep = pp[0][0].lower()
	np = chop_np(pp[1])
	
	if is_datetime(np['noun']):
		prep_type = 'datetime'
	else:
		prep_type = 'location'
		
	return {
		'prep': prep,
		'np': np,
		'prep_type': prep_type
	}
	

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