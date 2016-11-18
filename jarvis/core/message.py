from nltk import pos_tag, word_tokenize
from nltk.data import load
from nltk.tree import Tree
from jarvis.helpers.nlp.stanford_parser import parser
from jarvis.helpers.nlp.names import names_map
from itertools import groupby

tagdict = load('help/tagsets/upenn_tagset.pickle')


class Message:
	fp_prons = ['I', 'me', 'thou']
	fp_poss_prons = ['my', 'mine']
	sp_prons = ['you']
	sp_poss_prons = ['your', 'thy']
	
	def __init__(self, event):
		self.text = event['text']
		self.is_audio = event['isAudio']
		self.clean_text = self.text.lower().strip()
		self.tree = None
		
		if self.clean_text:
			self.tagged_text = self.tag_text(self.text)
			self.pos_map, self.pos_map_lc = self.create_pos_map()
		
	def tag_text(self, text):
		words = []
		
		for word in word_tokenize(text):
			if word == word.upper():
				word = word.lower()
			
			if word == 'i':
				word = 'I'
			
			words.append(word)
		
		return pos_tag(words)
	
	def create_pos_map(self):
		map = self.all_tags_map()
		lc_map = self.all_tags_map()
		
		for tagged_word in self.tagged_text:
			text, tag = tagged_word
			
			map[tag].append(text)
			
			if text != 'I': text = text.lower()
			lc_map[tag].append(text)
		
		return map, lc_map
	
	def all_tags_map(self):
		map = {}
	
		for tag in tagdict.keys():
			map[tag] = []
		
		return map
	
	def map_for_case(self, ignore_case):
		if ignore_case: return self.pos_map_lc
		return self.pos_map
	
	def has_pos(self, tag, text=None, ignore_case=True):
		map = self.map_for_case(ignore_case)
		if not text: return len(map[tag]) > 0
		if ignore_case: text = text.lower()
		return text in map[tag]
	
	def first_of_tag(self, tag, ignore_case=True):
		words = self.map_for_case(ignore_case)[tag]
		if not words: return None
		return words[0]
	
	def first_of_tag_after_tag(self, desired_tag, after_tag):
		tag_found = False
		
		for tagged_word in self.tagged_text:
			text, tag = tagged_word
			
			if tag == after_tag:
				tag_found = True
			else:
				if tag_found and tag == desired_tag:
					return text
				
		return None
	
	def get_tree(self, text=None):
		if text:
			tree = list(parser.raw_parse(text))[0]
		else:
			tree = self.tree or list(parser.raw_parse(self.text))[0]
			self.tree = tree
		
		return tree
	
	def is_person(self, subject):
		if subject not in self.clean_text: return False
		return bool(names_map.get(subject))
	
	def memory_comps(self, text=None):
		text = text or self.text
		t = self.get_tree(text)
		
		if not self.tree_has_memory_format(t): return None
		
		subject = self.strip_subject(t[0][0])
		if not subject: return None
		
		predicate = self.strip_predicate(t[0][1])
		if not predicate: return None
		
		return subject, predicate
		
	def strip_subject(self, tree):
		nps = self.group_subjects(tree)
		NOUN_LABELS = ['NN', 'NNS', 'NNP', 'NNPS', 'PRP', 'PRP$']
		nouns = []
		
		for np in nps:
			groups = self.labeled_leaves(np)
			pos = [g for g in groups if g[0] == 'POS' or g[0] == 'PRP$']
			owner = ''
			
			if pos:
				pos_index = groups.index(pos[0])
				pos_label, pos_text = pos[0]
				
				# if "'s", we want all joined text preceeding this
				if pos_label == 'POS':
					owner = ' '.join([g[1] for g in groups[:pos_index]])
				else:
					# if just a PRP$, that text is the owner
					owner = pos_text
				
				groups = groups[pos_index:]
				
			owned = [list(group) for k, group in groupby(groups, lambda g: g[0] not in NOUN_LABELS) if not k]
			
			n = []
			for o in owned:
				noun = ''
				
				for g in o:
					noun += ' {}'.format(g[1])
					
				noun = noun.strip()
				
				n.append({
					'noun': noun,
					'poss': owner
				})
					
			nouns.extend(n)
				
		return nouns
	
	def group_subjects(self, tree):
		NOUN_PHRASE = 'NP'
		POSSESSION = 'POS'
		groupings = []
		
		for child in tree:
			nps = self.children_with_label(child, NOUN_PHRASE)
			nps = [np for np in nps if self.children_with_label(np, NOUN_PHRASE) or not self.children_with_label(np, POSSESSION)]
			
			if nps:
				child_nps = [self.group_subjects(np) for np in nps]
				child_nps = [i for l in child_nps for i in l]  # flatten this out
				groupings.extend(child_nps)
			else:
				if isinstance(child, Tree) and child.label() == NOUN_PHRASE:
					groupings.append(child)
		
		if not groupings and tree.label() == NOUN_PHRASE:
			groupings = [tree]
		
		return groupings
	
	def strip_predicate(self, tree):
		STRIP_IF_LEAD = ['VBP', 'VBZ', 'MD']
		VERB_CONNECTORS = ['VB', 'VBD', 'VBN']
		ADJ_CONNECTORS = ['JJ', 'JJR', 'JJS']
		ADV_CONNECTORS = ['RB', 'RBR', 'RBS']
	
		pred_info = []
		sections = self.split_by_cc(tree)
		
		# For each section
		for t in sections:
			# Strip out certain leading verbs or modals
			if isinstance(t[0], Tree) and t[0].label() in STRIP_IF_LEAD:
				t = t[1]
			
			if t.label() == 'S':
				t = t[0]
				
			if t[0].label() == 'TO':
				t = t[1]
				
			sub_sections = self.split_by_cc(t)
						
			for s in sub_sections:
				preposition = None
				noun_info = None
				connectors = []
				descriptors = {'advs': [], 'adjs': []}
							
				if s.label() == 'NP':
					# TODO: still need to check for possession here (ex: Maggie is my girlfriend)
					# TODO: should still parse what you're adding here for where/when attributes (tomorrow at 5, in the morning, later, at the house, etc.)
					
					# get labeled leaves, split by CC's
					lls = [list(group) for k, group in groupby(self.labeled_leaves(s), lambda g: g[0] == 'CC') if not k]
					
					for ll in lls:
						descriptors['adjs'].append(' '.join([x[1] for x in ll if x[0] != 'DT']))
					
					pred_info.append({
						'noun': noun_info,
						'prep': preposition,
						'connectors': connectors,
						'descriptors': descriptors
					})
				elif s.label() == 'PP':
					for info in self.pp_info(s):
						prep, noun_info = info
						
						pred_info.append({
							'noun': noun_info,
							'prep': prep,
							'connectors': connectors,
							'descriptors': descriptors
						})
				else:
					# Chances are, s.label() == 'VP' at this point.
					
					# Separate out any non PP's
					non_pp = [c for c in s if isinstance(c, Tree) and c.label() != 'PP']
					
					# if non_pp is empty because s doesn't have any Tree children...
					if not non_pp and not [c for c in s if isinstance(c, Tree)] and len(s) > 0:
						# s will be the only non_pp
						non_pp = [s]
					
					groups = []
					
					# if PP(s) exists...
					if len(non_pp) != len(s):
						pps = [t for t in self.split_by_cc(s) if isinstance(t, Tree) and t.label() == 'PP'] or \
									[t for t in s if isinstance(t, Tree) and t.label() == 'PP']
							
						for pp in pps:
							groups.extend(self.pp_info(pp))
					else:
						nps = [c for c in non_pp if c.label() == 'NP']
						non_pp = [c for c in non_pp if c.label() != 'NP']
						
						for np in nps:
							for x in self.strip_subject(np):
								groups.append([None, x])  # preposition is None here
					
					labeled_leaves = []
					for x in non_pp:
						labeled_leaves.extend(self.labeled_leaves(x))
					
					for g in labeled_leaves:
						label, text = g
						
						if label in VERB_CONNECTORS:
							connectors.append(text)
						elif label in ADV_CONNECTORS:
							descriptors['advs'].append(text)
						elif label in ADJ_CONNECTORS:
							descriptors['adjs'].append(text)
							
					if groups:
						for group in groups:
							p, ni = group
							
							pred_info.append({
								'nouns': ni,
								'prep': p,
								'connectors': connectors,
								'descriptors': descriptors
							})
					else:
						pred_info.append({
							'nouns': None,
							'prep': None,
							'connectors': connectors,
							'descriptors': descriptors
						})
					
		return pred_info
	
	def pp_info(self, tree):
		# if PP of other PP's, get those. Otherwise, it'll just be the original one
		pps = [t for t in self.split_by_cc(tree) if t.label() == 'PP']
		
		info = []
		
		for pp in pps:
			prep, np = pp

			# if np has another nested PP, take care of that
			if [t.label() for t in np] == ['NP', 'PP']:
				for g in self.strip_subject(np[0]):
					info.append([prep[0], g])
					
				nested_pp = np[1]
				
				for g in self.strip_subject(nested_pp[1]):
					info.append([nested_pp[0][0], g])
			else:
				for g in self.strip_subject(np):
					info.append([prep[0], g])
				
		return info
	
	def labeled_leaves(self, tree):
		leaves = []
		
		for child in tree:
			if isinstance(child, Tree):
				leaves.extend(self.labeled_leaves(child))
			else:
				leaves.append([tree.label(), child])
		
		return leaves

	@staticmethod
	def children_with_label(tree, label):
		return [child for child in tree if isinstance(child, Tree) and child.label() == label]

	@staticmethod
	def tree_has_memory_format(tree):
		return tree[0].label() == 'S' \
					and len(tree[0]) == 2 \
					and tree[0][0].label() == 'NP' \
					and tree[0][1].label() == 'VP'

	@staticmethod
	def split_by_cc(tree):
		cc = [c for c in tree if isinstance(c, Tree) and c.label() == 'CC']
		
		if cc:
			return [c for c in tree if isinstance(c, Tree) and c.label() != 'CC']
		else:
			return [tree]
