import configparser
import datetime
import os
from tqdm import tqdm
import tensorflow as tf
from text_data import TextData
from model import Model
from test_mode import TestMode
from args import Args


class Trainer:
	MODEL_DIR_BASE = 'jarvis/learn/converse/tmp_model'
	MODEL_NAME_BASE = 'model'
	MODEL_EXT = '.ckpt'
	CONFIG_FILENAME = 'params.ini'
	CONFIG_VERSION = '0.3'
	TEST_IN_NAME = 'data/converse/test/samples.txt'
	TEST_OUT_SUFFIX = '_predictions.txt'
	SENTENCES_PREFIX = ['Q: ', 'A: ']
	
	def __init__(self):
		self.args = None
		self.text_data = None
		self.model = None  # seq2seq
		
		# Tensorflow utilities for convenience saving/logging
		self.writer = None
		self.saver = None
		self.model_dir = ''  # where the model is saved
		self.global_step = 0  # num iterations for current model
		
		# Tensorflow main session (keep track for the daemon)
		self.sess = None
			
	def prep_for_app_use(self):
		self.args = Args(None).parse_args()
		self.args.test = TestMode.DAEMON
		
		self.load_model_params()
		self.text_data = TextData(self.args)
		
		with tf.device(self.get_device()):
			self.model = Model(self.args, self.text_data)
		
		self.writer = tf.train.SummaryWriter(self._get_summary_name())
		self.saver = tf.train.Saver(max_to_keep=200)
		
		self.sess = tf.Session()
		self.sess.run(tf.initialize_all_variables())
		self.manage_previous_model(self.sess)
		
	# Training initialization
	def main(self, args=None):
		self.args = Args(args).parse_args()
		
		# Update self.model_dir and self.global_step...not used when loading our model,
		# but needs to be called before _get_summary_name)
		self.load_model_params()
		
		self.text_data = TextData(self.args)
		
		if self.args.create_dataset:
			print('Creating dataset and returning.')
			return
		
		with tf.device(self.get_device()):
			self.model = Model(self.args, self.text_data)
		
		# Saver/summaries
		self.writer = tf.train.SummaryWriter(self._get_summary_name())
		self.saver = tf.train.Saver(max_to_keep=200)  # Arbitrary limit ?
		
		# Running session
		self.sess = tf.Session()
		
		print('Initializing variables...')
		self.sess.run(tf.initialize_all_variables())
		
		# Reload the model (if it exists) if running in interactive or daemon mode
		if self.args.test != TestMode.ALL:
			self.manage_previous_model(self.sess)
		
		if self.args.test:
			if self.args.test == TestMode.INTERACTIVE:
				self.main_test_interactive(self.sess)
			elif self.args.test == TestMode.ALL:
				print('Start predicting...')
				self.predict_test_set(self.sess)
				print('All predictions done')
			elif self.args.test == TestMode.DAEMON:
				print('Daemon mode, running in background...')
			else:
				raise RuntimeError('Unknown test mode: {}'.format(self.args.test))
		else:
			self.main_train(self.sess)
		
		if self.args.test != TestMode.DAEMON:
			self.sess.close()
			print("Done.")
	
	# Training loop
	def main_train(self, sess):
		# Limit the number of training samples
		self.text_data.make_lighter(self.args.ratio_dataset)
		
		# Define the summary operator (Warning: Won't appear on the tensorboard graph)
		merged_summaries = tf.merge_all_summaries()
		
		if self.global_step == 0:  # Not restoring from previous run
			self.writer.add_graph(sess.graph)  # First time only
		
		# If restoring a model, restore the progression bar and the current batch?
		
		print('Start training (press Ctrl+C to save and exit)...')
		
		try:
			# Train!
			for e in range(self.args.num_epochs):
				print("\n----- Epoch {}/{} ; (lr={}) -----".format(e + 1, self.args.num_epochs, self.args.learning_rate))
				
				batches = self.text_data.get_batches()
				
				tic = datetime.datetime.now()
				for next_batch in tqdm(batches, desc="Training"):
					# Training pass
					ops, feed_dict = self.model.step(next_batch)
					
					# training, loss
					assert len(ops) == 2
					
					_, loss, summary = sess.run(ops + (merged_summaries,), feed_dict)
					
					self.writer.add_summary(summary, self.global_step)
					self.global_step += 1
					
					# Reached a checkpoint
					if self.global_step % self.args.save_every == 0:
						self._save_session(sess)
				
				toc = datetime.datetime.now()
				
				# Warning: Will overflow if an epoch takes more than 24 hours, and the output isn't really nicer
				print("Epoch finished in {}".format(toc - tic))
		
		# Exit program if user presses Ctrl+C while testing
		except (KeyboardInterrupt, SystemExit):
			print('Interruption detected, exiting the program...')
		
		# Ultimate saving before complete exit
		self._save_session(sess)
	
	# Try predicting the sentences from samples.txt.
	# The sentences are saved on the model_dir under the same name.
	def predict_test_set(self, sess):
		# Loading the file to predict
		with open(os.path.join(self.args.root_dir, self.TEST_IN_NAME), 'r') as f:
			lines = f.readlines()
		
		model_list = self._get_model_list()
		
		if not model_list:
			print('Warning: No model found in \'{}\'. Please train a model before trying to predict'.format(self.model_dir))
			return
		
		# Predicting for each model present in model_dir
		for model_name in sorted(model_list):
			print('Restoring previous model from {}'.format(model_name))
			self.saver.restore(sess, model_name)
			
			print('Testing...')
			
			# We remove the model extension and add the prediction suffix
			save_name = model_name[:-len(self.MODEL_EXT)] + self.TEST_OUT_SUFFIX
			
			with open(save_name, 'w') as f:
				nb_ignored = 0
				
				for line in tqdm(lines, desc='Sentences'):
					question = line[:-1]
					answer = self.single_predict(question)
					
					# If no answer, go back to the beginning to try again
					if not answer:
						nb_ignored += 1
						continue
					
					pred_string = '{x[0]}{0}\n{x[1]}{1}\n\n'.format(
						question,
						self.text_data.sequence2str(answer, clean=True),
						x=self.SENTENCES_PREFIX
					)
					
					if self.args.verbose:
						tqdm.write(pred_string)
						
					f.write(pred_string)
					
				print('Prediction finished, {}/{} sentences ignored (too long)'.format(nb_ignored, len(lines)))
	
	# Make predictions from user-input coming from console
	def main_test_interactive(self, sess):
		print("\n".join([
			'Welcome to the interactive mode. Here you can chat with Jarvis to see what predictions he makes.',
			'Type \'exit\' or just press ENTER to quit the program.'
		]))
		
		while True:
			question = raw_input(self.SENTENCES_PREFIX[0])
			
			if question.strip() == 'exit': break
			
			# Will contain the question as seen by the encoder
			question_seq = []
			answer = self.single_predict(question, question_seq)
			
			# If no answer, go back to the beginning to try again
			if not answer:
				print('Warning: sentence too long, sorry. Maybe try a simpler sentence.')
				continue
			
			print('{}{}'.format(self.SENTENCES_PREFIX[1], self.text_data.sequence2str(answer, clean=True)))
			
			if self.args.verbose:
				print(self.text_data.batch_seq2str(question_seq, clean=True, reverse=True))
				print(self.text_data.sequence2str(answer))
			
			print()
	
	# Predict a response
	# Args:
	# 	question (str): the raw input sentence
	# 	question_seq (List<int>): output argument. If given, will contain the input batch sequence.
	# Returns:
	# 	list <int>: the word ids corresponding to the answer
	def single_predict(self, question, question_seq=None):
		# Create the input batch
		batch = self.text_data.sentence2enco(question)
		if not batch:return None
		
		if question_seq is not None:  # If the caller wants to have the real input
			question_seq.extend(batch.encoder_seqs)
		
		# Run the model
		ops, feed_dict = self.model.step(batch)
		output = self.sess.run(ops[0], feed_dict)
		answer = self.text_data.deco2sentence(output)
		
		return answer
	
	# Return the answer to a given sentence (same as single_predict() but with additional cleaning)
	# Args:
	# 	sentence (str): the raw input sentence
	# Return:
	# 	str: the human readable sentence
	def daemon_predict(self, sentence):
		return self.text_data.sequence2str(self.single_predict(sentence), clean=True)
	
	# A utility function to close the daemon when finished
	def daemon_close(self):
		print('Exiting the daemon mode...')
		self.sess.close()
		print('Daemon closed.')
	
	# Restore or reset the model, depending on the parameters.
	# If the destination directory is not empty, it will handle the conflict as follows:
	#
	# 	- If '--reset' is set, all present files will be removed (warning: no confirmation is asked) and the training
	# 		will restart from scratch (global_step & cie reinitialized).
	#
	# 	- Otherwise, it will depend on the directory content. If the directory contains:
	# 			- No model files (only summary logs): works as a reset (restart from scratch)
	# 	 		- Other model files, but model_name not found (surely keep_all option changed): raise error, the user should
	# 	 			decide by himself what to do.
	#
	# 	- The right model file (eventually some other): no problem, simply resume the training.
	#
	# In any case, the directory will exist as it has been created by the summary writer
	def manage_previous_model(self, sess):
		model_name = self._get_model_name()
		
		if os.listdir(self.model_dir):
			if self.args.reset:
				print('Reset: Destroying previous model at {}'.format(self.model_dir))
				
			# Analysing directory content
			elif os.path.exists(model_name):  # Restore the model
				print('Restoring previous model from {}'.format(model_name))
				# Will crash when --reset is not activated and the model has not been saved yet
				self.saver.restore(sess, model_name)
				print('Model restored.')
				
			elif self._get_model_list():
				print('Conflict with previous models.')
				raise RuntimeError(
					'Some models are already present in \'{}\'. You should check them first (or re-try with the keep_all flag)'.format(
						self.model_dir
					)
				)
			
			# No other model to conflict with (probably summary files)
			else:
				print('No previous model found, but some files found at {}. Cleaning...'.format(self.model_dir))
				self.args.reset = True
			
			if self.args.reset:
				file_list = [os.path.join(self.model_dir, f) for f in os.listdir(self.model_dir)]
				for f in file_list:
					print('Removing {}'.format(f))
					os.remove(f)
		
		else:
			print('No previous model found, starting from clean directory: {}'.format(self.model_dir))
	
	# Save the model parameters and the variables
	def _save_session(self, sess):
		tqdm.write('Checkpoint reached: saving model (don\'t stop the run)...')
		self.save_model_params()
		self.saver.save(sess, self._get_model_name())
		tqdm.write('Model saved.')
	
	# Return the list of the model files inside the model directory
	def _get_model_list(self):
		return [os.path.join(self.model_dir, f) for f in os.listdir(self.model_dir) if f.endswith(self.MODEL_EXT)]
	
	# Load values associated with the current model, like the current global_step value.
	# For now, this function does not need to be called before loading the model (no parameters restored).
	# However, the model_dir name will be initialized here so it is required to call this function before
	# manage_previous_model(), _get_model_name() or _get_summary_name().
	# Warning: if you modify this function, make sure the changes mirror save_model_params, also check if the parameters
	# should be reset in manage_previous_model.
	def load_model_params(self):
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
						current_version,
						self.CONFIG_VERSION,
						config_name
					)
				)
			
			# Restoring the parameters
			self.global_step = config['General'].getint('global_step')
			# We need to restore the model length because of the textData associated and the vocabulary size.
			self.args.max_length = config['General'].getint('max_length')
			self.args.watson_mode = config['General'].getboolean('watson_mode')
			
			self.args.hidden_size = config['Network'].getint('hidden_size')
			self.args.num_layers = config['Network'].getint('num_layers')
			self.args.embedding_size = config['Network'].getint('embedding_size')
			self.args.softmax_samples = config['Network'].getint('softmax_samples')
			
			# No restoring for training params, batch size or other non model dependent parameters
			
			print("\n".join([
				'Warning: Restoring parameters:',
				'global_step: {}'.format(self.global_step),
				'max_length: {}'.format(self.args.max_length),
				'watson_mode: {}'.format(self.args.watson_mode),
				'hidden_size: {}'.format(self.args.hidden_size),
				'num_layers: {}'.format(self.args.num_layers),
				'embedding_size: {}'.format(self.args.embedding_size),
				'softmax_samples: {}'.format(self.args.softmax_samples)
			]))
		
		# For now, not arbitrary, independent max_length between encoder and decoder.
		self.args.max_length_enco = self.args.max_length
		self.args.max_length_deco = self.args.max_length + 2
		
		if self.args.watson_mode:
			self.SENTENCES_PREFIX.reverse()
	
	# Save the params of the model, like the current global_step value.
	# Warning: if you modify this function, make sure the changes mirror load_model_params.
	def save_model_params(self):
		config = configparser.ConfigParser()
		
		config['General'] = {
			'version': self.CONFIG_VERSION,
			'global_step': str(self.global_step),
			'max_length': str(self.args.max_length),
			'watson_mode': str(self.args.watson_mode)
		}

		config['Network'] = {
			'hidden_size': str(self.args.hidden_size),
			'num_layers': str(self.args.num_layers),
			'embedding_size': str(self.args.embedding_size),
			'softmax_samples': str(self.args.softmax_samples)
		}
		
		# Keep track of the learning params (but without restoring them).
		config['Training (won\'t be restored)'] = {
			'learning_rate': str(self.args.learning_rate),
			'batch_size': str(self.args.batch_size)
		}
		
		with open(os.path.join(self.model_dir, self.CONFIG_FILENAME), 'w') as config_file:
			config.write(config_file)
	
	# Where to save the summary.
	def _get_summary_name(self):
		return self.model_dir
	
	# Where to save/load the model. Is called at each checkpoint and the first time the model
	# is loaded. If the --keep_all option is set, the global step value will be included in the name.
	def _get_model_name(self):
		model_name = os.path.join(self.model_dir, self.MODEL_NAME_BASE)
		
		if self.args.keep_all:
			model_name += '-' + str(self.global_step)
		
		return model_name + self.MODEL_EXT
	
	# On which device should we run the model?
	def get_device(self):
		device = self.args.device
		
		valid_devices = {
			'cpu': '/cpu:0',
			'gpu': '/gpu:0'
		}
		
		if not device or device not in valid_devices.keys():
			return None
		
		return valid_devices[device]
