import random


def all_greetings():
	return [
		'Hey there!',
		'Greetings!',
		'Greetings to you too!',
		'What up home skillet biscuit?',
		'Hey!',
		'Hi there!',
		'Hey man!',
		'Hey dude!',
	]


def random_greeting():
	ag = all_greetings()
	ag_len = len(ag)
	return ag[random.randint(0, ag_len - 1)]
