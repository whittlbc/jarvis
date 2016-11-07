import numpy as np
import nltk
from tqdm import tqdm
import pickle
import math
import os
import random
from cornell_data import CornellData
from batch import Batch


# Monkey patch math.isclose for Python <3.5
if not hasattr(math, 'isclose'):
	math.isclose = lambda a, b, rel_tol=1e-09, abs_tol=0.0: \
		abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


# Dataset class (Warning: No vocab limit currently)
class TextData:
	
	# Load all conversations
	def __init__(self, args):
		# Model parameters
		self.args = args
		
		# Path variables
		self.corpus_dir = os.path.join(self.args.root_dir, 'data/converse/cornell/')
		self.samples_dir = os.path.join(self.args.root_dir, 'data/converse/samples/')
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
	
	# Return the name of the dataset that the program should use with the current parameters.
	# Compute this from the base name, the given tag (self.args.dataset_tag) and the sentence length.
	def _construct_name(self):
		base_name = 'dataset'
		
		if self.args.dataset_tag:
			base_name += '-' + self.args.dataset_tag
			
		return base_name + '-' + str(self.args.max_length) + '.pkl'
	
	# Only keep a small fraction of the dataset, given by the ratio
	def make_lighter(self, ratio_dataset):
		if not math.isclose(ratio_dataset, 1.0):
			self.shuffle()
			print('WARNING: Ratio feature not implemented.')
		pass
	
	# Shuffle the training samples
	def shuffle(self):
		print("Shuffling the dataset...")
		random.shuffle(self.training_samples)
	
	# Create a single batch from the sample list. The batch size is automatically defined by the number of
	# samples given. The inputs should already be inverted, and the target should already have <go> and <eos>.
	# Warning: This function should not make direct calls to args.batch_size.
	# Args:
	# 		samples (list<Obj>): a list of samples, each sample being of the form: [input, target]
	# Return:
	# 		Batch: a batch object
	def _create_batch(self, samples):
		batch = Batch()
		batch_size = len(samples)
		
		# Create the batch tensor
		for i in range(batch_size):
			# Unpack the sample
			sample = samples[i]
			
			# Watson mode: invert question and answer
			if not self.args.test and self.args.watson_mode:
				sample = list(reversed(sample))
			
			# Reverse inputs (and not outputs) -- a trick defined in the original seq2seq paper.
			batch.encoder_seqs.append(list(reversed(sample[0])))
			# Add the <go> and <eos> tokens.
			batch.decoder_seqs.append([self.go_token] + sample[1] + [self.eos_token])
			# Same as decoder, but shifted to the left (ignore the <go>).
			batch.target_seqs.append(batch.decoder_seqs[-1][1:])
			
			# Long sentences should have been filtered during the dataset creation.
			assert len(batch.encoder_seqs[i]) <= self.args.max_length_enco
			assert len(batch.decoder_seqs[i]) <= self.args.max_length_deco
			
			# Add padding & define weight
			batch.encoder_seqs[i] = [self.pad_token] * \
															(self.args.max_length_enco - len(batch.encoder_seqs[i])) + \
															batch.encoder_seqs[i]  # Left padding for the input
			
			batch.weights.append([1.0] * len(batch.target_seqs[i]) + [0.0] * (self.args.max_length_deco - len(batch.target_seqs[i])))
			batch.decoder_seqs[i] = batch.decoder_seqs[i] + [self.pad_token] * (self.args.max_length_deco - len(batch.decoder_seqs[i]))
			batch.target_seqs[i] = batch.target_seqs[i] + [self.pad_token] * (self.args.max_length_deco - len(batch.target_seqs[i]))
		
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
		
		return batch
	
	# Prepare the batches for the current epoch
	# Return:
	# 	list<Batch>: get a list of the batches for the next epoch.
	def get_batches(self):
		self.shuffle()
		batches = []
		
		# Generator over the mini-batch training samples
		def gen_next_samples():
			for i in range(0, self.get_sample_size(), self.args.batch_size):
				yield self.training_samples[i:min(i + self.args.batch_size, self.get_sample_size())]
		
		for samples in gen_next_samples():
			batch = self._create_batch(samples)
			batches.append(batch)
			
		return batches
	
	# Return size of the dataset
	def get_sample_size(self):
		return len(self.training_samples)
	
	# Return number of words in dataset
	def get_vocabulary_size(self):
		return len(self.word2id)
	
	# Load/create the conversations data
	def load_corpus(self, dir_name):
		if not os.path.exists(os.path.join(dir_name, self.samples_name)):
			print('Training samples not found. Creating dataset...')
			
			# Corpus creation
			cornell_dataset = CornellData(self.corpus_dir)
			self.create_corpus(cornell_dataset.get_conversations())
			
			# Saving tf samples
			print('Saving dataset...')
			self.save_dataset(dir_name)
		else:
			print('Loading dataset from {}...'.format(dir_name))
			self.load_dataset(dir_name)
		
		assert self.pad_token == 0
	
	# Save samples to file
	def save_dataset(self, dir_name):
		with open(os.path.join(dir_name, self.samples_name), 'wb') as handle:
			# Warning: If adding something here, also modifying load_dataset
			data = {
				"word2id": self.word2id,
				"id2word": self.id2word,
				"training_samples": self.training_samples
			}
			
			# Using the highest protocol available
			pickle.dump(data, handle, -1)
	
	# Load samples from file
	def load_dataset(self, dir_name):
		with open(os.path.join(dir_name, self.samples_name), 'rb') as handle:
			# Warning: If adding something here, also modifying save_dataset
			data = pickle.load(handle)
			self.word2id = data["word2id"]
			self.id2word = data["id2word"]
			self.training_samples = data["training_samples"]
			self.pad_token = self.word2id["<pad>"]
			self.go_token = self.word2id["<go>"]
			self.eos_token = self.word2id["<eos>"]
			self.unknown_token = self.word2id["<unknown>"]  # Restore special words
	
	# Extract all data from the given vocabulary
	def create_corpus(self, conversations):
		# Add standard tokens
		self.pad_token = self.get_word_id("<pad>")  # Padding (Warning: first things to add > id=0 !!)
		self.go_token = self.get_word_id("<go>")  # Start of sequence
		self.eos_token = self.get_word_id("<eos>")  # End of sequence
		self.unknown_token = self.get_word_id("<unknown>")  # Word dropped from vocabulary
		
		# Preprocessing data. The dataset will be saved in the same order it has been extracted.
		for conversation in tqdm(conversations, desc="Extract conversations"):
			self.extract_conversation(conversation)
	
	# Extract sample lines from the conversations.
	# Args:
	# 		conversation (Obj): a conversation object containing the lines to extract
	def extract_conversation(self, conversation):
		# Iterate over all lines in the conversation except for the last (since there's no answer for it)
		for i in range(len(conversation["lines"]) - 1):
			input_line = conversation["lines"][i]
			target_line = conversation["lines"][i + 1]
			
			input_words = self.extract_text(input_line["text"])
			target_words = self.extract_text(target_line["text"], True)
			
			# Filter wrong samples (if one of the list is empty)
			if input_words and target_words:
				self.training_samples.append([input_words, target_words])
	
	# Extract the words from sample lines
	# Args:
	# 		line (str): a line containing the text to extract
	# 		is_target (bool): Define the question on the answer
	# Return:
	# 		list<int>: list of the word ids of a sentence
	def extract_text(self, line, is_target=False):
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
				
				# Create the vocabulary and the training sentences
				for token in tokens:
					temp_words.append(self.get_word_id(token))
				
				if is_target:
					words = words + temp_words
				else:
					words = temp_words + words
			else:
				# We reached the max length already
				break
		
		return words
	
	# Get the id of the word (and add it to the dictionary if not existing). If the word does not exist and
	# create is set to False, the function will return the unknown_token value.
	# Args:
	# 		word (str): word to add
	# 		create (Bool): if True and the word does not exist already, the world will be added
	# Return:
	# 		int: the id of the word created
	def get_word_id(self, word, create=True):
		# Should we only keep words with more than one occurrence?
		word = word.lower()
		
		# Get the id if the word already exists.
		word_id = self.word2id.get(word, -1)
		
		# If not, create a new entry.
		if word_id == -1:
			if create:
				word_id = len(self.word2id)
				self.word2id[word] = word_id
				self.id2word[word_id] = word
			else:
				word_id = self.unknown_token
		
		return word_id
	
	# Print a complete batch, useful for debugging
	def print_batch(self, batch):
		print('----- Print batch -----')
		
		for i in range(len(batch.encoder_seqs[0])):  # Batch size
			print("\n".join([
				'Encoder: {}'.format(self.batch_seq2str(batch.encoder_seqs, seq_id=i)),
				'Decoder: {}'.format(self.batch_seq2str(batch.decoder_seqs, seq_id=i)),
				'Targets: {}'.format(self.batch_seq2str(batch.target_seqs, seq_id=i)),
				'Weights: {}'.format(' '.join([str(weight) for weight in [batch_weight[i] for batch_weight in batch.weights]]))
			]))
	
	# Convert a list of integers into a human readable string
	# Args:
	# 		sequence (list<int>): the sentence to print
	# 		clean (Bool): if set, remove the <go>, <pad> and <eos> tokens
	# 		reverse (Bool): for the input, option to restore the standard order
	# Return:
	# 		str: the sentence
	def sequence2str(self, sequence, clean=False, reverse=False):
		if not sequence: return ''
		if not clean: return ' '.join([self.id2word[idx] for idx in sequence])
		
		sentence = []
		
		for word_id in sequence:
			# If end of generated sentence...
			if word_id == self.eos_token:
				break
			elif word_id != self.pad_token and word_id != self.go_token:
				sentence.append(self.id2word[word_id])
		
		# Reverse means input so no <eos> (otherwise pb with previous early stop)
		if reverse:
			sentence.reverse()
			
		return self.prettify(sentence)
	
	# Convert a list of integer into a human readable string. The difference between the previous
	# function is that on a batch object, the values have been reorganized as batch instead of sentence.
	# Args:
	# 		batch_seq (list<list<int>>): the sentence(s) to print
	# 		seq_id (int): the position of the sequence inside the batch
	# 		kwargs: the formatting options( See sequence2str() )
	# Return:
	# 		str: the sentence
	def batch_seq2str(self, batch_seq, seq_id=0, **kwargs):
		sequence = []
		
		for i in range(len(batch_seq)):
			sequence.append(batch_seq[i][seq_id])
		
		return self.sequence2str(sequence, **kwargs)
	
	# Encode a sequence and return a batch as an input for the model
	def sentence2enco(self, sentence):
		if sentence == '': return None
		
		# (1) Divide the sentence in token
		tokens = nltk.word_tokenize(sentence)
		
		if len(tokens) > self.args.max_length:
			return None
		
		# (2) Convert the token in word ids
		word_ids = []
		
		# Create the vocabulary and the training sentences
		for token in tokens:
			word_ids.append(self.get_word_id(token, create=False))
		
		# (3) Create the batch (add padding, reverse)
		batch = self._create_batch([[word_ids, []]])  # Mono batch, no target output
		
		return batch
	
	# Decode the output of the decoder and return a human friendly sentence
	# Args:
	# 		decoder_outputs (list<np.array>)
	def deco2sentence(self, decoder_outputs):
		sequence = []
		
		# Choose the words with the highest prediction score
		for out in decoder_outputs:
			# Adding each predicted word ids
			sequence.append(np.argmax(out))
		
		# Return the raw sentence. Let the caller do some cleaning eventually.
		return sequence
	
	@staticmethod
	def prettify(words):
		sentence = ''
			
		i = 0
		for word in words:
			# Capitalize first word
			if i == 0 and not word.isupper():
				word = word.title()
			
			# always capitalize i's
			elif word == 'i':
				word = 'I'
				
			if i == 0 or word in [',', '?', '!', ';', ':', '.'] or word.startswith("'"):
				sentence += word
			else:
				sentence += ' {}'.format(word)
				
			i += 1
		
		return sentence
			
	# Print a random dialogue from the dataset
	def play_dataset(self):
		print('Randomly playing samples:')
		
		for i in range(self.args.play_dataset):
			id_sample = random.randint(0, len(self.training_samples))
			
			print("\n".join([
				'Q: {}'.format(self.sequence2str(self.training_samples[id_sample][0])),
				'A: {}'.format(self.sequence2str(self.training_samples[id_sample][1]))
			]) + "\n")

		pass
