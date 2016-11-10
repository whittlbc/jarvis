from nltk import pos_tag, word_tokenize
from nltk.data import load
tagdict = load('help/tagsets/upenn_tagset.pickle')
from nltk.internals import find_jars_within_path
from nltk.parse.stanford import StanfordParser
from nltk.corpus import names
from nltk.tree import Tree
from itertools import groupby
import code

parser = StanfordParser(model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz")
stanford_dir = parser._classpath[0].rpartition('/')[0]
parser._classpath = tuple(find_jars_within_path(stanford_dir))

names_map = dict(
	[(name.lower(), 'male') for name in names.words('male.txt')] +
	[(name.lower(), 'female') for name in names.words('female.txt')]
)


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
	
	def memory_components(self, text):
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
		VERB_CONNECTORS = ['VB', 'VBD', 'VBN']
		STRIP_IF_LEAD = ['VBP', 'VBZ', 'MD']
		pred_info = []
		
		sections = self.split_by_cc(tree)
		
		# For each section
		for t in sections:
			# Remove leading verb if type is in STRIP_IF_LEAD
			if isinstance(t[0], Tree) and t[0].label() in STRIP_IF_LEAD:
				t = t[1]
			
			sub_sections = self.split_by_cc(t)
						
			for s in sub_sections:
				# TODO: Take care of what happens when PP's aren't directly here...nested under another S
				# "going to" fucks things up
				
				non_pp = [c for c in s if isinstance(c, Tree) and c.label() != 'PP']
				pp_info = None
				
				# if PP exists...
				if len(non_pp) != len(s):
					pps = [c for c in s if isinstance(c, Tree) and c.label() == 'PP']
					pp_cc = [c for c in pps if isinstance(c, Tree) and c.label() == 'CC']
					
					if pp_cc:
						pps = [c for c in pps if isinstance(c, Tree) and c.label() == 'PP']
						
					for pp in pps:
						prep, np = pp
						
						if prep.label() != 'IN':
							print 'Section of PP not an IN! -- it was a {}'.format(prep.label())

						if np.label() != 'NP':
							print 'Section of PP not an NP! -- it was a {}'.format(np.label())
						
						pp_info = [prep[0], self.strip_subject(np)]
				
				connector = []
				for n in non_pp:
					connector.extend(self.labeled_leaves(n))
					
				# TODO: Need to add in support for more than just verbs...adjectives and nouns
				# Ex: Maggie is cool
				# Ex: Maggie is my girlfriend
				connector = ' '.join([g[1] for g in connector if g[0] in VERB_CONNECTORS])
														
				pred_info.append([connector, pp_info])
					
		return pred_info

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
