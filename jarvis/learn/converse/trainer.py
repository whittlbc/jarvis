import argparse
import configparser
import datetime
import os
from tqdm import tqdm
import tensorflow as tf
from text_data import TextData
from model import Model


class Trainer:
	
	class TestMode:
		ALL = 'all'
		INTERACTIVE = 'interactive'  # The user can write his own questions
		DAEMON = 'daemon'  # The chatbot runs on background and can regularly be called to predict something
	
	def __init__(self):
		# Model/dataset parameters
		self.args = None
		
		# Task specific object
		self.text_data = None  # Dataset
		self.model = None  # Sequence to sequence model
		
		# Tensorflow utilities for convenience saving/logging
		self.writer = None
		self.saver = None
		self.model_dir = ''  # Where the model is saved
		self.global_step = 0  # Represent the number of iteration for the current model
		
		# Tensorflow main session (we keep track for the daemon)
		self.sess = None
		
		# Filename and directories constants
		self.MODEL_DIR_BASE = 'jarvis/learn/converse/models'
		self.MODEL_NAME_BASE = 'model'
		self.MODEL_EXT = '.ckpt'
		self.CONFIG_FILENAME = 'params.ini'
		self.CONFIG_VERSION = '0.3'
		self.TEST_IN_NAME = 'data/converse/test/samples.txt'
		self.TEST_OUT_SUFFIX = '_predictions.txt'
		self.SENTENCES_PREFIX = ['Q: ', 'A: ']
	
	# Parse the arguments from the given command line
	@staticmethod
	def parse_args(args):
		parser = argparse.ArgumentParser()
		
		# Global options
		global_args = parser.add_argument_group('Global options')
		global_args.add_argument('--test', nargs='?',
														 choices=[Trainer.TestMode.ALL, Trainer.TestMode.INTERACTIVE, Trainer.TestMode.DAEMON],
														 const=Trainer.TestMode.ALL, default=None,
														 help='if present, launch the program try to answer all sentences from data/converse/test/ with the defined model(s), in interactive mode, the user can wrote his own sentences, use daemon mode to integrate the chatbot in another program')
		global_args.add_argument('--create_dataset', action='store_true',
														 help='if present, the program will only generate the dataset from the corpus (no training/testing)')
		global_args.add_argument('--play_dataset', type=int, nargs='?', const=10, default=None,
														 help='if set, the program  will randomly play some samples(can be use conjointly with create_dataset if this is the only action you want to perform)')
		global_args.add_argument('--reset', action='store_true',
														 help='use this if you want to ignore the previous model present on the model directory (Warning: the model will be destroyed with all the folder content)')
		global_args.add_argument('--verbose', action='store_true',
														 help='When testing, will plot the outputs at the same time they are computed')
		global_args.add_argument('--keep_all', action='store_true',
														 help='If this option is set, all saved model will be keep (Warning: make sure you have enough free disk space or increase save_every)')  # TODO: Add an option to delimit the max size
		global_args.add_argument('--model_tag', type=str, default=None,
														 help='tag to differentiate which model to store/load')
		global_args.add_argument('--root_dir', type=str, default=None, help='folder where to look for the models and data')
		global_args.add_argument('--watson_mode', action='store_true',
														 help='Inverse the questions and answer when training (the network try to guess the question)')
		global_args.add_argument('--device', type=str, default=None,
														 help='\'gpu\' or \'cpu\' (Warning: make sure you have enough free RAM), allow to choose on which hardware run the model')
		global_args.add_argument('--seed', type=int, default=None, help='random seed for replication')
		
		# Dataset options
		dataset_args = parser.add_argument_group('Dataset options')
		dataset_args.add_argument('--corpus', type=str, default='cornell',
															help='corpus on which extract the dataset. Only one corpus available right now (Cornell)')
		dataset_args.add_argument('--dataset_tag', type=str, default=None,
															help='add a tag to the dataset (file where to load the vocabulary and the precomputed samples, not the original corpus). Useful to manage multiple versions')  # The samples are computed from the corpus if it does not exist already. There are saved in \'data/converse/samples/\'
		dataset_args.add_argument('--ratio_dataset', type=float, default=1.0,
															help='ratio of dataset used to avoid using the whole dataset')  # Not implemented, useless ?
		dataset_args.add_argument('--max_length', type=int, default=10,
															help='maximum length of the sentence (for input and output), define number of maximum step of the RNN')
		
		# Network options (Warning: if modifying something here, also make the change on save/loadParams() )
		nn_args = parser.add_argument_group('Network options', 'architecture related option')
		nn_args.add_argument('--hidden_size', type=int, default=256, help='number of hidden units in each RNN cell')
		nn_args.add_argument('--num_layers', type=int, default=2, help='number of rnn layers')
		nn_args.add_argument('--embedding_size', type=int, default=32, help='embedding size of the word representation')
		nn_args.add_argument('--softmax_samples', type=int, default=0,
												 help='Number of samples in the sampled softmax loss function. A value of 0 deactivates sampled softmax')
		
		# Training options
		training_args = parser.add_argument_group('Training options')
		training_args.add_argument('--num_epochs', type=int, default=30, help='maximum number of epochs to run')
		training_args.add_argument('--save_every', type=int, default=1000,
															 help='nb of mini-batch step before creating a model checkpoint')
		training_args.add_argument('--batch_size', type=int, default=10, help='mini-batch size')
		training_args.add_argument('--learning_rate', type=float, default=0.001, help='Learning rate')
		
		return parser.parse_args(args)
	
	# General initialization
	def main(self, args=None):
		self.args = self.parse_args(args)
		
		if not self.args.root_dir:
			self.args.root_dir = os.getcwd()  # Use the current working directory
		
		# tf.logging.set_verbosity(tf.logging.INFO) # DEBUG, INFO, WARN (default), ERROR, or FATAL
		
		self.load_model_params()  # Update the self.model_dir and self.global_step, for now, not used when loading Model (but need to be called before _get_summary_name)
		
		self.text_data = TextData(self.args)
		# TODO: Add a mode where we can force the input of the decoder // Try to visualize the predictions for
		# each word of the vocabulary / decoder input
		# TODO: For now, the model are trained for a specific dataset (because of the max_length which define the
		# vocabulary). Add a compatibility mode which allow to launch a model trained on a different vocabulary (
		# remap the word2id/id2word variables).
		if self.args.create_dataset:
			print('Dataset created! Thanks for using this program')
			return  # No need to go further
		
		with tf.device(self.get_device()):
			self.model = Model(self.args, self.text_data)
		
		# Saver/summaries
		self.writer = tf.train.SummaryWriter(self._get_summary_name())
		self.saver = tf.train.Saver(max_to_keep=200)  # Arbitrary limit ?
		
		# TODO: Fixed seed (WARNING: If dataset shuffling, make sure to do that after saving the
		# dataset, otherwise, all which cames after the shuffling won't be replicable when
		# reloading the dataset). How to restore the seed after loading ??
		# Also fix seed for random.shuffle (does it works globally for all files ?)
		
		# Running session
		
		self.sess = tf.Session()  # TODO: Replace all sess by self.sess (not necessary a good idea) ?
		
		print('Initialize variables...')
		self.sess.run(tf.initialize_all_variables())
		
		# Reload the model eventually (if it exist.), on testing mode, the models are not loaded here (but in predict_test_set)
		if self.args.test != Trainer.TestMode.ALL:
			self.manage_previous_model(self.sess)
		
		if self.args.test:
			# TODO: For testing, add a mode where instead taking the most likely output after the <go> token,
			# takes the second or third so it generates new sentences for the same input. Difficult to implement,
			# probably have to modify the TensorFlow source code
			if self.args.test == Trainer.TestMode.INTERACTIVE:
				self.main_test_interactive(self.sess)
			elif self.args.test == Trainer.TestMode.ALL:
				print('Start predicting...')
				self.predict_test_set(self.sess)
				print('All predictions done')
			elif self.args.test == Trainer.TestMode.DAEMON:
				print('Daemon mode, running in background...')
			else:
				raise RuntimeError('Unknown test mode: {}'.format(self.args.test))  # Should never happen
		else:
			self.main_train(self.sess)
		
		if self.args.test != Trainer.TestMode.DAEMON:
			self.sess.close()
			print("The End! Thanks for using this program")
	
	def main_train(self, sess):
		""" Training loop
		Args:
				sess: The current running session
		"""
		
		# Specific training dependent loading
		
		self.text_data.make_lighter(self.args.ratio_dataset)  # Limit the number of training samples
		
		# Define the summary operator (Warning: Won't appear on the tensorboard graph)
		merged_summaries = tf.merge_all_summaries()
		
		if self.global_step == 0:  # Not restoring from previous run
			self.writer.add_graph(sess.graph)  # First time only
		
		# If restoring a model, restore the progression bar ? and current batch ?
		
		print('Start training (press Ctrl+C to save and exit)...')
		
		try:  # If the user exit while training, we still try to save the model
			for e in range(self.args.num_epochs):
				
				print()
				print("----- Epoch {}/{} ; (lr={}) -----".format(e + 1, self.args.num_epochs, self.args.learning_rate))
				
				batches = self.text_data.get_batches()
				
				# TODO: Also update learning parameters eventually
				
				tic = datetime.datetime.now()
				for nextBatch in tqdm(batches, desc="Training"):
					# Training pass
					ops, feed_dict = self.model.step(nextBatch)
					assert len(ops) == 2  # training, loss
					_, loss, summary = sess.run(ops + (merged_summaries,), feed_dict)
					self.writer.add_summary(summary, self.global_step)
					self.global_step += 1
					
					# Checkpoint
					if self.global_step % self.args.save_every == 0:
						self._save_session(sess)
				
				toc = datetime.datetime.now()
				
				print("Epoch finished in {}".format(
					toc - tic))  # Warning: Will overflow if an epoch takes more than 24 hours, and the output isn't really nicer
		except (KeyboardInterrupt, SystemExit):  # If the user press Ctrl+C while testing progress
			print('Interruption detected, exiting the program...')
		
		self._save_session(sess)  # Ultimate saving before complete exit
	
	def predict_test_set(self, sess):
		""" Try predicting the sentences from the samples.txt file.
		The sentences are saved on the model_dir under the same name
		Args:
				sess: The current running session
		"""
		
		# Loading the file to predict
		with open(os.path.join(self.args.root_dir, self.TEST_IN_NAME), 'r') as f:
			lines = f.readlines()
		
		model_list = self._get_model_list()
		
		if not model_list:
			print('Warning: No model found in \'{}\'. Please train a model before trying to predict'.format(self.model_dir))
			return
		
		# Predicting for each model present in model_dir
		for model_name in sorted(model_list):  # TODO: Natural sorting
			print('Restoring previous model from {}'.format(model_name))
			self.saver.restore(sess, model_name)
			print('Testing...')
			
			save_name = model_name[:-len(
				self.MODEL_EXT)] + self.TEST_OUT_SUFFIX  # We remove the model extension and add the prediction suffix
			
			with open(save_name, 'w') as f:
				nb_ignored = 0
				
				for line in tqdm(lines, desc='Sentences'):
					question = line[:-1]
					answer = self.single_predict(question)
					
					if not answer:
						nb_ignored += 1
						continue  # Back to the beginning, try again
					
					pred_string = '{x[0]}{0}\n{x[1]}{1}\n\n'.format(question, self.text_data.sequence2str(answer, clean=True),
																													x=self.SENTENCES_PREFIX)
					if self.args.verbose:
						tqdm.write(pred_string)
					f.write(pred_string)
				print('Prediction finished, {}/{} sentences ignored (too long)'.format(nb_ignored, len(lines)))
	
	def main_test_interactive(self, sess):
		""" Try predicting the sentences that the user will enter in the console
		Args:
				sess: The current running session
		"""
		# TODO: If verbose mode, also show similar sentences from the training set with the same words (include in mainTest also)
		# TODO: Also show the top 10 most likely predictions for each predicted output (when verbose mode)
		# TODO: Log the questions asked for latter re-use (merge with test/samples.txt)
		
		print('Testing: Launch interactive mode:')
		print('')
		print('Welcome to the interactive mode, here you can ask to Deep Q&A the sentence you want. Don\'t have high '
					'expectation. Type \'exit\' or just press ENTER to quit the program. Have fun.')
		
		while True:
			question = input(self.SENTENCES_PREFIX[0])
			if question == '' or question == 'exit':
				break
			
			question_seq = []  # Will be contain the question as seen by the encoder
			answer = self.single_predict(question, question_seq)
			if not answer:
				print('Warning: sentence too long, sorry. Maybe try a simpler sentence.')
				continue  # Back to the beginning, try again
			
			print('{}{}'.format(self.SENTENCES_PREFIX[1], self.text_data.sequence2str(answer, clean=True)))
			
			if self.args.verbose:
				print(self.text_data.batch_seq2str(question_seq, clean=True, reverse=True))
				print(self.text_data.sequence2str(answer))
			
			print()
	
	def single_predict(self, question, question_seq=None):
		""" Predict the sentence
		Args:
				question (str): the raw input sentence
				question_seq (List<int>): output argument. If given will contain the input batch sequence
		Return:
				list <int>: the word ids corresponding to the answer
		"""
		# Create the input batch
		batch = self.text_data.sentence2enco(question)
		
		if not batch:
			return None
		if question_seq is not None:  # If the caller want to have the real input
			question_seq.extend(batch.encoder_seqs)
		
		# Run the model
		ops, feed_dict = self.model.step(batch)
		output = self.sess.run(ops[0], feed_dict)  # TODO: Summarize the output too (histogram, ...)
		answer = self.text_data.deco2sentence(output)
		
		return answer
	
	def daemon_predict(self, sentence):
		""" Return the answer to a given sentence (same as single_predict() but with additional cleaning)
		Args:
				sentence (str): the raw input sentence
		Return:
				str: the human readable sentence
		"""
		return self.text_data.sequence2str(self.single_predict(sentence), clean=True)
	
	def daemon_close(self):
		""" A utility function to close the daemon when finish
		"""
		print('Exiting the daemon mode...')
		self.sess.close()
		print('Daemon closed.')
	
	def manage_previous_model(self, sess):
		""" Restore or reset the model, depending of the parameters
		If the destination directory already contains some file, it will handle the conflict as following:
		 * If --reset is set, all present files will be removed (warning: no confirmation is asked) and the training
		 restart from scratch (global_step & cie reinitialized)
		 * Otherwise, it will depend of the directory content. If the directory contains:
			 * No model files (only summary logs): works as a reset (restart from scratch)
			 * Other model files, but model_name not found (surely keep_all option changed): raise error, the user should
			 decide by himself what to do
			 * The right model file (eventually some other): no problem, simply resume the training
		In any case, the directory will exist as it has been created by the summary writer
		Args:
				sess: The current running session
		"""
		
		model_name = self._get_model_name()
		
		if os.listdir(self.model_dir):
			if self.args.reset:
				print('Reset: Destroying previous model at {}'.format(self.model_dir))
			# Analysing directory content
			elif os.path.exists(model_name):  # Restore the model
				print('Restoring previous model from {}'.format(model_name))
				self.saver.restore(sess,
													 model_name)  # Will crash when --reset is not activated and the model has not been saved yet
				print('Model restored.')
			elif self._get_model_list():
				print('Conflict with previous models.')
				raise RuntimeError(
					'Some models are already present in \'{}\'. You should check them first (or re-try with the keep_all flag)'.format(
						self.model_dir))
			else:  # No other model to conflict with (probably summary files)
				print('No previous model found, but some files found at {}. Cleaning...'.format(
					self.model_dir))  # Warning: No confirmation asked
				self.args.reset = True
			
			if self.args.reset:
				file_list = [os.path.join(self.model_dir, f) for f in os.listdir(self.model_dir)]
				for f in file_list:
					print('Removing {}'.format(f))
					os.remove(f)
		
		else:
			print('No previous model found, starting from clean directory: {}'.format(self.model_dir))
	
	def _save_session(self, sess):
		""" Save the model parameters and the variables
		Args:
				sess: the current session
		"""
		tqdm.write('Checkpoint reached: saving model (don\'t stop the run)...')
		self.save_model_params()
		self.saver.save(sess, self._get_model_name())  # TODO: Put a limit size (ex: 3GB for the model_dir)
		tqdm.write('Model saved.')
	
	def _get_model_list(self):
		""" Return the list of the model files inside the model directory
		"""
		return [os.path.join(self.model_dir, f) for f in os.listdir(self.model_dir) if f.endswith(self.MODEL_EXT)]
	
	def load_model_params(self):
		""" Load the some values associated with the current model, like the current global_step value
		For now, this function does not need to be called before loading the model (no parameters restored). However,
		the model_dir name will be initialized here so it is required to call this function before manage_previous_model(),
		_get_model_name() or _get_summary_name()
		Warning: if you modify this function, make sure the changes mirror save_model_params, also check if the parameters
		should be reset in manage_previous_model
		"""
		# Compute the current model path
		self.model_dir = os.path.join(self.args.root_dir, self.MODEL_DIR_BASE)
		if self.args.model_tag:
			self.model_dir += '-' + self.args.model_tag
		
		# If there is a previous model, restore some parameters
		config_name = os.path.join(self.model_dir, self.CONFIG_FILENAME)
		
		if not self.args.reset and not self.args.create_dataset and os.path.exists(config_name):
			# Loading
			config = configparser.ConfigParser()
			config.read(config_name)
			
			# Check the version
			current_version = config['General'].get('version')
			if current_version != self.CONFIG_VERSION:
				raise UserWarning(
					'Present configuration version {0} does not match {1}. You can try manual changes on \'{2}\''.format(
						current_version, self.CONFIG_VERSION, config_name))
			
			# Restoring the the parameters
			self.global_step = config['General'].getint('global_step')
			self.args.max_length = config['General'].getint(
				'max_length')  # We need to restore the model length because of the textData associated and the vocabulary size (TODO: Compatibility mode between different max_length)
			self.args.watson_mode = config['General'].getboolean('watson_mode')
			# self.args.dataset_tag = config['General'].get('dataset_tag')
			
			self.args.hidden_size = config['Network'].getint('hidden_size')
			self.args.num_layers = config['Network'].getint('num_layers')
			self.args.embedding_size = config['Network'].getint('embedding_size')
			self.args.softmax_samples = config['Network'].getint('softmax_samples')
			
			# No restoring for training params, batch size or other non model dependent parameters
			
			# Show the restored params
			print()
			print('Warning: Restoring parameters:')
			print('global_step: {}'.format(self.global_step))
			print('max_length: {}'.format(self.args.max_length))
			print('watson_mode: {}'.format(self.args.watson_mode))
			print('hidden_size: {}'.format(self.args.hidden_size))
			print('num_layers: {}'.format(self.args.num_layers))
			print('embedding_size: {}'.format(self.args.embedding_size))
			print('softmax_samples: {}'.format(self.args.softmax_samples))
			print()
		
		# For now, not arbitrary  independent max_length between encoder and decoder
		self.args.max_length_enco = self.args.max_length
		self.args.max_length_deco = self.args.max_length + 2
		
		if self.args.watson_mode:
			self.SENTENCES_PREFIX.reverse()
	
	def save_model_params(self):
		""" Save the params of the model, like the current global_step value
		Warning: if you modify this function, make sure the changes mirror load_model_params
		"""
		config = configparser.ConfigParser()
		config['General'] = {}
		config['General']['version'] = self.CONFIG_VERSION
		config['General']['global_step'] = str(self.global_step)
		config['General']['max_length'] = str(self.args.max_length)
		config['General']['watson_mode'] = str(self.args.watson_mode)
		
		config['Network'] = {}
		config['Network']['hidden_size'] = str(self.args.hidden_size)
		config['Network']['num_layers'] = str(self.args.num_layers)
		config['Network']['embedding_size'] = str(self.args.embedding_size)
		config['Network']['softmax_samples'] = str(self.args.softmax_samples)
		
		# Keep track of the learning params (but without restoring them)
		config['Training (won\'t be restored)'] = {}
		config['Training (won\'t be restored)']['learning_rate'] = str(self.args.learning_rate)
		config['Training (won\'t be restored)']['batch_size'] = str(self.args.batch_size)
		
		with open(os.path.join(self.model_dir, self.CONFIG_FILENAME), 'w') as config_file:
			config.write(config_file)
	
	def _get_summary_name(self):
		""" Parse the argument to decide were to save the summary, at the same place that the model
		The folder could already contain logs if we restore the training, those will be merged
		Return:
				str: The path and name of the summary
		"""
		return self.model_dir
	
	def _get_model_name(self):
		""" Parse the argument to decide were to save/load the model
		This function is called at each checkpoint and the first time the model is load. If keep_all option is set, the
		global_step value will be included in the name.
		Return:
				str: The path and name were the model need to be saved
		"""
		model_name = os.path.join(self.model_dir, self.MODEL_NAME_BASE)
		
		if self.args.keep_all:  # We do not erase the previously saved model by including the current step on the name
			model_name += '-' + str(self.global_step)
		
		return model_name + self.MODEL_EXT
	
	def get_device(self):
		""" Parse the argument to decide on which device run the model
		Return:
				str: The name of the device on which run the program
		"""
		if self.args.device == 'cpu':
			return '/cpu:0'
		elif self.args.device == 'gpu':
			return '/gpu:0'
		elif self.args.device is None:  # No specified device (default)
			return None
		else:
			print('Warning: Error in the device name: {}, use the default device'.format(self.args.device))
			return None
