import argparse
import os
from test_mode import TestMode


def parse_args(args):
	parser = argparse.ArgumentParser()
	
	groups = [
		global_options,
		dataset_options,
		network_options,
		training_options
	]
	
	for group in groups:
		group_name = group.__name__.replace('_', ' ').title()
		args_group = parser.add_argument_group(group_name)
		
		for arg_info in group():
			args_group.add_argument(arg_info['arg'], **arg_info['options'])
	
	return parser.parse_args(args)
	
	
def global_options():
	return [
		{
			'arg': '--test',
			'options': {
				'nargs': '?',
				'choices': [TestMode.ALL, TestMode.INTERACTIVE, TestMode.DAEMON],
				'const': TestMode.ALL,
				'default': None,
				'help': 'if present, launch the program try to answer all sentences from data/converse/test/ with the defined model(s), in interactive mode, the user can wrote his own sentences, use daemon mode to integrate the chatbot in another program'
			}
		},
		{
			'arg': '--create_dataset',
			'options': {
				'action': 'store_true',
				'help': 'if present, the program will only generate the dataset from the corpus (no training/testing)'
			}
		},
		{
			'arg': '--play_dataset',
			'options': {
				'type': int,
				'nargs': '?',
				'const': 10,
				'default': None,
				'help': 'if set, the program will randomly play some samples(can be use conjointly with create_dataset if this is the only action you want to perform)'
			}
		},
		{
			'arg': '--reset',
			'options': {
				'action': 'store_true',
				'help': 'use this if you want to ignore the previous model present on the model directory (Warning: the model will be destroyed with all the folder content)'
			}
		},
		{
			'arg': '--verbose',
			'options': {
				'action': 'store_true',
				'help': 'When testing, will plot the outputs at the same time they are computed'
			}
		},
		{
			'arg': '--keep_all',
			'options': {
				'action': 'store_true',
				'help': 'If this option is set, all saved model will be keep (Warning: make sure you have enough free disk space or increase save_every)'
			}
		},
		{
			'arg': '--model_tag',
			'options': {
				'type': str,
				'default': None,
				'help': 'tag to differentiate which model to store/load'
			}
		},
		{
			'arg': '--root_dir',
			'options': {
				'type': str,
				'default': os.getcwd(),
				'help': 'folder where to look for the models and data'
			}
		},
		{
			'arg': '--watson_mode',
			'options': {
				'action': 'store_true',
				'help': 'Inverse the questions and answer when training (the network try to guess the question)'
			}
		},
		{
			'arg': '--device',
			'options': {
				'type': str,
				'default': None,
				'help': '\'gpu\' or \'cpu\' (Warning: make sure you have enough free RAM), allow to choose on which hardware run the model'
			}
		},
		{
			'arg': '--seed',
			'options': {
				'type': int,
				'default': None,
				'help': 'random seed for replication'
			}
		}
	]


def dataset_options():
	return [
		{
			'arg': '--corpus',
			'options': {
				'type': str,
				'default': 'cornell',
				'help': 'corpus on which extract the dataset. Only one corpus available right now (Cornell)'
			}
		},
		{
			'arg': '--dataset_tag',
			'options': {
				'type': str,
				'default': None,
				'help': 'add a tag to the dataset (file where to load the vocabulary and the precomputed samples, not the original corpus). Useful to manage multiple versions'
			}
		},
		{
			'arg': '--ratio_dataset',
			'options': {
				'type': float,
				'default': 1.0,
				'help': 'ratio of dataset used to avoid using the whole dataset'
			}
		},
		{
			'arg': '--max_length',
			'options': {
				'type': int,
				'default': 10,
				'help': 'maximum length of the sentence (for input and output), define number of maximum step of the RNN'
			}
		}
	]


# WARNING: ** if modifying something here, also make the change on save/loadParams() **
def network_options():
	return [
		{
			'arg': '--hidden_size',
			'options': {
				'type': int,
				'default': 256,
				'help': 'number of hidden units in each RNN cell'
			}
		},
		{
			'arg': '--num_layers',
			'options': {
				'type': int,
				'default': 2,
				'help': 'number of rnn layers'
			}
		},
		{
			'arg': '--embedding_size',
			'options': {
				'type': int,
				'default': 32,
				'help': 'embedding size of the word representation'
			}
		},
		{
			'arg': '--softmax_samples',
			'options': {
				'type': int,
				'default': 0,
				'help': 'Number of samples in the sampled softmax loss function. A value of 0 deactivates sampled softmax'
			}
		}
	]


def training_options():
	return [
		{
			'arg': '--num_epochs',
			'options': {
				'type': int,
				'default': 30,
				'help': 'maximum number of epochs to run'
			}
		},
		{
			'arg': '--save_every',
			'options': {
				'type': int,
				'default': 1000,
				'help': 'nb of mini-batch step before creating a model checkpoint'
			}
		},
		{
			'arg': '--batch_size',
			'options': {
				'type': int,
				'default': 10,
				'help': 'mini-batch size'
			}
		},
		{
			'arg': '--learning_rate',
			'options': {
				'type': float,
				'default': 0.001,
				'help': 'Learning rate'
			}
		}
	]