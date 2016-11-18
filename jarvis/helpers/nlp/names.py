from nltk.corpus import names

names_map = dict(
	[(name.lower(), 'male') for name in names.words('male.txt')] +
	[(name.lower(), 'female') for name in names.words('female.txt')]
)