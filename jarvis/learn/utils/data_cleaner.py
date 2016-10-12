import re
from nltk.tokenize import word_tokenize
from nltk.stem.snowball import SnowballStemmer


class DataCleaner:
	stemmer = SnowballStemmer('english')

	# inputs is an array or list
	def clean(self, inputs):
		return map(self.clean_input, inputs)
	
	def clean_input(self, input):
		# Get rid of anything but letters, numbers, and spaces:
		input = re.sub('[^ \w]+', '', input[0])
		# Stem all the words after tokenizing the input:
		stemmed_words = map(lambda x: self.stemmer.stem(x), word_tokenize(input))
		# Join the words joined back together into one string
		return ' '.join(stemmed_words)