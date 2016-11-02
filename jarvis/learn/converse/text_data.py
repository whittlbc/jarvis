import numpy as np
import nltk
from tqdm import tqdm
import pickle
import math
import os
import random
from cornell_data import CornellData

# Monkey patch math.isclose for Python <3.5
if not hasattr(math, 'isclose'):
	math.isclose = lambda a, b, rel_tol=1e-09, abs_tol=0.0: \
		abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


class Batch:
	def __init__(self):
		self.encoder_seqs = []
		self.decoder_seqs = []
		self.target_seqs = []
		self.weights = []


class TextData:
	"""Dataset class
	Warning: No vocabulary limit
	"""
	
	def __init__(self, args):
		"""Load all conversations
		Args:
				args: parameters of the model
		"""
		# Model parameters
		self.args = args
		
		# Path variables
		self.corpus_dir = os.path.join(self.args.rootDir, 'data/converse/cornell/')
		self.samples_dir = os.path.join(self.args.rootDir, 'data/converse/samples/')
		self.samples_name = self._construct_name()
		
		self.pad_token = -1  # Padding
		self.go_token = -1  # Start of sequence
		self.eos_token = -1  # End of sequence
		self.unknown_token = -1  # Word dropped from vocabulary
		
		self.training_samples = []  # 2d array containing each question and his answer [[input,target]]
		
		self.word2id = {}
		self.id2word = {}  # For a rapid conversion
		
		self.load_corpus(self.samples_dir)
		
		# Plot some stats:
		print('Loaded: {} words, {} QA'.format(len(self.word2id), len(self.training_samples)))
		
		if self.args.play_dataset:
			self.play_dataset()
	
	def _construct_name(self):
		"""Return the name of the dataset that the program should use with the current parameters.
		Computer from the base name, the given tag (self.args.dataset_tag) and the sentence length
		"""
		base_name = 'dataset'
		
		if self.args.dataset_tag:
			base_name += '-' + self.args.dataset_tag
		return base_name + '-' + str(self.args.max_length) + '.pkl'
	
	def make_lighter(self, ratio_dataset):
		"""Only keep a small fraction of the dataset, given by the ratio
		"""
		if not math.isclose(ratio_dataset, 1.0):
			self.shuffle()  # Really ?
			print('WARNING: Ratio feature not implemented !!!')
		pass
	
	def shuffle(self):
		"""Shuffle the training samples
		"""
		print("Shuffling the dataset...")
		random.shuffle(self.training_samples)
	
	def _create_batch(self, samples):
		"""Create a single batch from the list of sample. The batch size is automatically defined by the number of
		samples given.
		The inputs should already be inverted. The target should already have <go> and <eos>
		Warning: This function should not make direct calls to args.batch_size !!!
		Args:
				samples (list<Obj>): a list of samples, each sample being on the form [input, target]
		Return:
				Batch: a batch object en
		"""
		
		batch = Batch()
		batch_size = len(samples)
		
		# Create the batch tensor
		for i in range(batch_size):
			# Unpack the sample
			sample = samples[i]
			if not self.args.test and self.args.watson_mode:  # Watson mode: invert question and answer
				sample = list(reversed(sample))
			batch.encoder_seqs.append(list(
				reversed(sample[0])))  # Reverse inputs (and not outputs), little trick as defined on the original seq2seq paper
			batch.decoder_seqs.append([self.go_token] + sample[1] + [self.eos_token])  # Add the <go> and <eos> tokens
			batch.target_seqs.append(batch.decoder_seqs[-1][1:])  # Same as decoder, but shifted to the left (ignore the <go>)
			
			# Long sentences should have been filtered during the dataset creation
			assert len(batch.encoder_seqs[i]) <= self.args.max_length_enco
			assert len(batch.decoder_seqs[i]) <= self.args.max_length_deco
			
			# Add padding & define weight
			batch.encoder_seqs[i] = [self.pad_token] * (self.args.max_length_enco - len(batch.encoder_seqs[i])) + \
															batch.encoder_seqs[i]  # Left padding for the input
			batch.weights.append(
				[1.0] * len(batch.target_seqs[i]) + [0.0] * (self.args.max_length_deco - len(batch.target_seqs[i])))
			batch.decoder_seqs[i] = batch.decoder_seqs[i] + [self.pad_token] * (
			self.args.max_length_deco - len(batch.decoder_seqs[i]))
			batch.target_seqs[i] = batch.target_seqs[i] + [self.pad_token] * (
			self.args.max_length_deco - len(batch.target_seqs[i]))
		
		# Simple hack to reshape the batch
		encoder_seqs_t = []  # Corrected orientation
		for i in range(self.args.max_length_enco):
			encoder_seq_t = []
			for j in range(batch_size):
				encoder_seq_t.append(batch.encoder_seqs[j][i])
			encoder_seqs_t.append(encoder_seq_t)
		batch.encoder_seqs = encoder_seqs_t
		
		decoder_seqs_t = []
		target_seqs_t = []
		weights_t = []
		
		for i in range(self.args.max_length_deco):
			decoder_seq_t = []
			target_seq_t = []
			weight_t = []
			for j in range(batch_size):
				decoder_seq_t.append(batch.decoder_seqs[j][i])
				target_seq_t.append(batch.target_seqs[j][i])
				weight_t.append(batch.weights[j][i])
			decoder_seqs_t.append(decoder_seq_t)
			target_seqs_t.append(target_seq_t)
			weights_t.append(weight_t)
		
		batch.decoder_seqs = decoder_seqs_t
		batch.target_seqs = target_seqs_t
		batch.weights = weights_t
		
		# # Debug
		# self.print_batch(batch)  # Input inverted, padding should be correct
		# print(self.sequence2str(samples[0][0]))
		# print(self.sequence2str(samples[0][1]))  # Check we did not modified the original sample
		
		return batch
	
	def get_batches(self):
		"""Prepare the batches for the current epoch
		Return:
				list<Batch>: Get a list of the batches for the next epoch
		"""
		self.shuffle()
		
		batches = []
		
		def gen_next_samples():
			""" Generator over the mini-batch training samples
			"""
			for i in range(0, self.get_sample_size(), self.args.batch_size):
				yield self.training_samples[i:min(i + self.args.batch_size, self.get_sample_size())]
		
		for samples in gen_next_samples():
			batch = self._create_batch(samples)
			batches.append(batch)
		return batches
	
	def get_sample_size(self):
		"""Return the size of the dataset
		Return:
				int: Number of training samples
		"""
		return len(self.training_samples)
	
	def get_vocabulary_size(self):
		"""Return the number of words present in the dataset
		Return:
				int: Number of word on the loader corpus
		"""
		return len(self.word2id)
	
	def load_corpus(self, dir_name):
		"""Load/create the conversations data
		Args:
				dir_name (str): The directory where to load/save the model
		"""
		dataset_exist = False
		if os.path.exists(os.path.join(dir_name, self.samples_name)):
			dataset_exist = True
		
		if not dataset_exist:  # First time we load the database: creating all files
			print('Training samples not found. Creating dataset...')
			# Corpus creation
			cornell_dataset = CornellData(self.corpus_dir)
			self.create_corpus(cornell_dataset.get_conversations())
			
			# Saving
			print('Saving dataset...')
			self.save_dataset(dir_name)  # Saving tf samples
		else:
			print('Loading dataset from {}...'.format(dir_name))
			self.load_dataset(dir_name)
		
		assert self.pad_token == 0
	
	def save_dataset(self, dir_name):
		"""Save samples to file
		Args:
				dir_name (str): The directory where to load/save the model
		"""
		
		with open(os.path.join(dir_name, self.samples_name), 'wb') as handle:
			data = {  # Warning: If adding something here, also modifying load_dataset
				"word2id": self.word2id,
				"id2word": self.id2word,
				"training_samples": self.training_samples
			}
			pickle.dump(data, handle, -1)  # Using the highest protocol available
	
	def load_dataset(self, dir_name):
		"""Load samples from file
		Args:
				dir_name (str): The directory where to load the model
		"""
		with open(os.path.join(dir_name, self.samples_name), 'rb') as handle:
			data = pickle.load(handle)  # Warning: If adding something here, also modifying save_dataset
			self.word2id = data["word2id"]
			self.id2word = data["id2word"]
			self.training_samples = data["training_samples"]
			
			self.pad_token = self.word2id["<pad>"]
			self.go_token = self.word2id["<go>"]
			self.eos_token = self.word2id["<eos>"]
			self.unknown_token = self.word2id["<unknown>"]  # Restore special words
	
	def create_corpus(self, conversations):
		"""Extract all data from the given vocabulary
		"""
		# Add standard tokens
		self.pad_token = self.get_word_id("<pad>")  # Padding (Warning: first things to add > id=0 !!)
		self.go_token = self.get_word_id("<go>")  # Start of sequence
		self.eos_token = self.get_word_id("<eos>")  # End of sequence
		self.unknown_token = self.get_word_id("<unknown>")  # Word dropped from vocabulary
		
		# Preprocessing data
		
		for conversation in tqdm(conversations, desc="Extract conversations"):
			self.extract_conversation(conversation)
			
			# The dataset will be saved in the same order it has been extracted
	
	def extract_conversation(self, conversation):
		"""Extract the sample lines from the conversations
		Args:
				conversation (Obj): a conversation object containing the lines to extract
		"""
		
		# Iterate over all the lines of the conversation
		for i in range(len(conversation["lines"]) - 1):  # We ignore the last line (no answer for it)
			input_line = conversation["lines"][i]
			target_line = conversation["lines"][i + 1]
			
			input_words = self.extract_text(input_line["text"])
			target_words = self.extract_text(target_line["text"], True)
			
			if input_words and target_words:  # Filter wrong samples (if one of the list is empty)
				self.training_samples.append([input_words, target_words])
	
	def extract_text(self, line, is_target=False):
		"""Extract the words from a sample lines
		Args:
				line (str): a line containing the text to extract
				is_target (bool): Define the question on the answer
		Return:
				list<int>: the list of the word ids of the sentence
		"""
		words = []
		
		# Extract sentences
		sentences_token = nltk.sent_tokenize(line)
		
		# We add sentence by sentence until we reach the maximum length
		for i in range(len(sentences_token)):
			# If question: we only keep the last sentences
			# If answer: we only keep the first sentences
			if not is_target:
				i = len(sentences_token) - 1 - i
			
			tokens = nltk.word_tokenize(sentences_token[i])
			
			# If the total length is not too big, we still can add one more sentence
			if len(words) + len(tokens) <= self.args.max_length:
				temp_words = []
				for token in tokens:
					temp_words.append(self.get_word_id(token))  # Create the vocabulary and the training sentences
				
				if is_target:
					words = words + temp_words
				else:
					words = temp_words + words
			else:
				break  # We reach the max length already
		
		return words
	
	def get_word_id(self, word, create=True):
		"""Get the id of the word (and add it to the dictionary if not existing). If the word does not exist and
		create is set to False, the function will return the unknown_token value
		Args:
				word (str): word to add
				create (Bool): if True and the word does not exist already, the world will be added
		Return:
				int: the id of the word created
		"""
		# Should we Keep only words with more than one occurrence ?
		
		word = word.lower()  # Ignore case
		
		# Get the id if the word already exist
		word_id = self.word2id.get(word, -1)
		
		# If not, we create a new entry
		if word_id == -1:
			if create:
				word_id = len(self.word2id)
				self.word2id[word] = word_id
				self.id2word[word_id] = word
			else:
				word_id = self.unknown_token
		
		return word_id
	
	def print_batch(self, batch):
		"""Print a complete batch, useful for debugging
		Args:
				batch (Batch): a batch object
		"""
		print('----- Print batch -----')
		for i in range(len(batch.encoder_seqs[0])):  # Batch size
			print('Encoder: {}'.format(self.batch_seq2str(batch.encoder_seqs, seq_id=i)))
			print('Decoder: {}'.format(self.batch_seq2str(batch.decoder_seqs, seq_id=i)))
			print('Targets: {}'.format(self.batch_seq2str(batch.target_seqs, seq_id=i)))
			print(
			'Weights: {}'.format(' '.join([str(weight) for weight in [batch_weight[i] for batch_weight in batch.weights]])))
	
	def sequence2str(self, sequence, clean=False, reverse=False):
		"""Convert a list of integer into a human readable string
		Args:
				sequence (list<int>): the sentence to print
				clean (Bool): if set, remove the <go>, <pad> and <eos> tokens
				reverse (Bool): for the input, option to restore the standard order
		Return:
				str: the sentence
		"""
		
		if not sequence:
			return ''
		
		if not clean:
			return ' '.join([self.id2word[idx] for idx in sequence])
		
		sentence = []
		for word_id in sequence:
			if word_id == self.eos_token:  # End of generated sentence
				break
			elif word_id != self.pad_token and word_id != self.go_token:
				sentence.append(self.id2word[word_id])
		
		if reverse:  # Reverse means input so no <eos> (otherwise pb with previous early stop)
			sentence.reverse()
		
		return ' '.join(sentence)
	
	def batch_seq2str(self, batch_seq, seq_id=0, **kwargs):
		"""Convert a list of integer into a human readable string.
		The difference between the previous function is that on a batch object, the values have been reorganized as
		batch instead of sentence.
		Args:
				batch_seq (list<list<int>>): the sentence(s) to print
				seq_id (int): the position of the sequence inside the batch
				kwargs: the formatting options( See sequence2str() )
		Return:
				str: the sentence
		"""
		sequence = []
		for i in range(len(batch_seq)):  # Sequence length
			sequence.append(batch_seq[i][seq_id])
		
		return self.sequence2str(sequence, **kwargs)
	
	def sentence2enco(self, sentence):
		"""Encode a sequence and return a batch as an input for the model
		Return:
				Batch: a batch object containing the sentence, or none if something went wrong
		"""
		
		if sentence == '':
			return None
		
		# First step: Divide the sentence in token
		tokens = nltk.word_tokenize(sentence)
		if len(tokens) > self.args.max_length:
			return None
		
		# Second step: Convert the token in word ids
		word_ids = []
		for token in tokens:
			word_ids.append(self.get_word_id(token, create=False))  # Create the vocabulary and the training sentences
		
		# Third step: creating the batch (add padding, reverse)
		batch = self._create_batch([[word_ids, []]])  # Mono batch, no target output
		
		return batch
	
	def deco2sentence(self, decoder_outputs):
		"""Decode the output of the decoder and return a human friendly sentence
		decoder_outputs (list<np.array>):
		"""
		sequence = []
		
		# Choose the words with the highest prediction score
		for out in decoder_outputs:
			sequence.append(np.argmax(out))  # Adding each predicted word ids
		
		return sequence  # We return the raw sentence. Let the caller do some cleaning eventually
	
	def play_dataset(self):
		"""Print a random dialogue from the dataset
		"""
		print('Randomly play samples:')
		for i in range(self.args.play_dataset):
			id_sample = random.randint(0, len(self.training_samples))
			print('Q: {}'.format(self.sequence2str(self.training_samples[id_sample][0])))
			print('A: {}'.format(self.sequence2str(self.training_samples[id_sample][1])))
			print()
		pass
