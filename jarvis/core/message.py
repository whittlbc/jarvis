from nltk import pos_tag, word_tokenize
from nltk.data import load
tagdict = load('help/tagsets/upenn_tagset.pickle')


class Message:
	fp_poss_prons = ['my', 'mine']
	sp_poss_prons = ['your', 'thy']
	sp_prons = ['you']
	
	def __init__(self, text):
		self.text = text
		self.clean_text = text.lower().strip()
		
		if self.clean_text:
			self.tagged_text = pos_tag(word_tokenize(text))
			self.pos_map, self.pos_map_lc = self.create_pos_map()
		
	def create_pos_map(self):
		map = self.all_tags_map()
		lc_map = self.all_tags_map()
		
		for tagged_word in self.tagged_text:
			text, tag = tagged_word
			map[tag].append(text)
			lc_map[tag].append(text.lower())
		
		return map, lc_map
	
	def all_tags_map(self):
		map = {}

		for tag in tagdict.keys():
			map[tag] = []
		
		return map
	
	def map_for_case(self, tag, ignore_case):
		if ignore_case:
			map = self.pos_map_lc
		else:
			map = self.pos_map
		
		if tag not in map:
			raise 'POS tag does not exist in the map: {}'.format(tag)

		return map
	
	def has_pos(self, tag, text=None, ignore_case=True):
		map = self.map_for_case(tag, ignore_case)
		if not text: return len(map[tag]) > 0
		if ignore_case: text = text.lower()
		return text in map[tag]
	
	def first_of_tag(self, tag, ignore_case=True):
		map = self.map_for_case(tag, ignore_case)
		return map[tag][0]
	
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
