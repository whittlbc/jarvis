from nltk.internals import find_jars_within_path
from nltk.parse.stanford import StanfordParser


p = StanfordParser(model_path="edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz")
stanford_dir = p._classpath[0].rpartition('/')[0]
p._classpath = tuple(find_jars_within_path(stanford_dir))


def parser():
	return p


class Clauses:
	DECLARATION = 'S'
	RELATIVE_CLAUSE = 'SBAR'
	DIRECT_WH_QUESTION = 'SBARQ'
	INVERTED_DECLARATION = 'SINV'
	INVERTED_YES_NO = 'SQ'
	

class Phrases:
	ADJ_PHRASE = 'ADJP'
	ADV_PHRASE = 'ADVP'
	CONJUNCTION_PHRASE = 'CONJP'
	FRAGMENT = 'FRAG'
	INTERJECTION = 'INTJ'
	LIST = 'LST'
	NOT_A_CONSTITUENT = 'NAC'
	NOUN_PHRASE = 'NP'
	COMPLEX_NP = 'NX'
	PREP_PHRASE = 'PP'
	PARENTHETICAL = 'PRN'
	PARTICLE = 'PRT'
	QUANTIFIER_PHRASE = 'QP'
	REDUCED_REL_CLAUSE = 'RRC'
	UNLIKE_COORD_PHRASE = 'UCP'
	VERB_PHRASE = 'VP'
	WH_ADJ_PHRASE = 'WHADJP'
	WH_ADV_PHRASE = 'WHAVP'
	WH_NOUN_PHRASE = 'WHNP'
	WH_PREP_PHRASE = 'WHPP'
	UNKNOWN = 'X'
	
	
class Words:
	COORD_CONJUNC = 'CC'
	NUMBER = 'CD'
	DETERMINER = 'DT'
	EXISTENTIAL_THERE = 'EX'
	FOREIGN = 'FW'
	PREP = 'IN'
	ADJ = 'JJ'
	ADJ_COMPARATIVE = 'JJR'
	ADJ_SUPERLATIVE = 'JJS'
	LIST_ITEM = 'LS'
	MODAL = 'MD'
	NOUN_SINGULAR = 'NN'
	NOUN_PLURAL = 'NNS'
	PROPER_NOUN_SINGULAR = 'NNP'
	PROPER_NOUN_PLURAL= 'NNPS'
	PREDETERMINER = 'PDT'
	POSSESSIVE_ENDING = 'POS'
	PERSONAL_PRONOUN = 'PRP'
	POSSESSIVE_PRONOUN = 'PRP$'
	ADV = 'RB'
	ADV_COMPARATIVE = 'RBR'
	ADV_SUPERLATIVE = 'RBS'
	PARTICLE = 'RP'
	SYMBOL = 'SYM'
	TO = 'TO'
	INTERJECTION = 'UH'
	VERB = 'VB'
	VERB_PAST = 'VBD'
	VERB_GERUND = 'VBG'
	VERB_PAST_PARTICIPLE = 'VBN'
	VERB_NON_3P_SING_PRESENT = 'VBP'
	VERB_3P_SING_PRESENT = 'VBZ'
	WH_DETERMINER = 'WDT'
	WH_PRONOUN = 'WP'
	POSSESSIVE_WH_PRONOUN = 'WP$'
	WH_ADVERB = 'WRB'


clauses = Clauses()
phrases = Phrases()
words = Words()


def word_labels():
	return labels_for(Words)
					
					
def phrase_labels():
	return labels_for(Phrases)


def clause_labels():
	return labels_for(Clauses)


def all_labels():
	return word_labels() + phrase_labels() + clause_labels()
			
			
def labels_for(klass):
	return [value for name, value in vars(klass).iteritems() if not name.startswith('_')]


def nouns(include_words=True, include_pronouns=True, include_phrases=False, include_wh=False):
	labels = []
	
	if include_words:
		labels += [
			words.NOUN_SINGULAR,
			words.NOUN_PLURAL,
			words.PROPER_NOUN_SINGULAR,
			words.PROPER_NOUN_PLURAL
		]
		
	if include_pronouns:
		labels += [
			words.PERSONAL_PRONOUN,
			words.POSSESSIVE_PRONOUN
		]
		
		if include_wh:
			labels += [
				words.WH_PRONOUN,
				words.POSSESSIVE_WH_PRONOUN
			]
		
	if include_phrases:
		labels += [phrases.NOUN_PHRASE]
		
		if include_wh:
			labels += [phrases.WH_NOUN_PHRASE]
			
	return set(labels)


def verbs(include_words=True, include_phrases=False):
	labels = []
	
	if include_words:
		labels += [
			words.VERB,
			words.VERB_PAST,
			words.VERB_GERUND,
			words.VERB_PAST_PARTICIPLE,
			words.VERB_NON_3P_SING_PRESENT,
			words.VERB_3P_SING_PRESENT,
		]
	
	if include_phrases:
		labels += [phrases.VERB_PHRASE]
		
	return set(labels)


def adjectives(include_words=True, include_phrases=False, include_wh=False):
	labels = []
	
	if include_words:
		labels += [
			words.ADJ,
			words.ADJ_COMPARATIVE,
			words.ADJ_SUPERLATIVE
		]
	
	if include_phrases:
		labels += [phrases.ADJ_PHRASE]
		
		if include_wh:
			labels += [phrases.WH_ADJ_PHRASE]
	
	return set(labels)


def adverbs(include_words=True, include_phrases=False, include_wh=False):
	labels = []
	
	if include_words:
		labels += [
			words.ADV,
			words.ADV_COMPARATIVE,
			words.ADV_SUPERLATIVE
		]
			
		if include_wh:
			labels += [words.WH_ADVERB]
	
	if include_phrases:
		labels += [phrases.ADV_PHRASE]
		
		if include_wh:
			labels += [phrases.WH_ADV_PHRASE]

	return set(labels)


nouns = nouns()
verbs = verbs()
adjectives = adjectives()
adverbs = adverbs()