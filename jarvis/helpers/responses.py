import random


def greeting():
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


def whatup():
	return [
		'Not much.',
		"Just chillin'. How bout you?"
	]
	

def random_greeting():
	return random_selection(greeting())


def random_whatup():
	return random_selection(whatup())


def random_selection(options):
	return options[random.randint(0, len(options) - 1)]
