import tensorflow as tf
from batch import Batch


class ProjectionOp:
	""" Single layer perceptron
	Project input tensor on the output dimension
	"""
	
	def __init__(self, shape, scope=None, dtype=None):
		"""
		Args:
				shape: a tuple (input dim, output dim)
				scope (str): encapsulate variables
				dtype: the weights type
		"""
		assert len(shape) == 2
		
		self.scope = scope
		
		# Projection on the keyboard
		with tf.variable_scope('weights_' + self.scope):
			self.W = tf.get_variable(
				'weights',
				shape,
				# initializer=tf.truncated_normal_initializer()  # TODO: Tune value (fct of input size: 1/sqrt(input_dim))
				dtype=dtype
			)
			self.b = tf.get_variable(
				'bias',
				shape[1],
				initializer=tf.constant_initializer(),
				dtype=dtype
			)
	
	def get_weights(self):
		""" Convenience method for some tf arguments
		"""
		return self.W, self.b
	
	def __call__(self, X):
		""" Project the output of the decoder into the vocabulary space
		Args:
				X (tf.Tensor): input value
		"""
		with tf.name_scope(self.scope):
			return tf.matmul(X, self.W) + self.b


class Model:
	"""
	Implementation of a seq2seq model.
	Architecture:
			Encoder/decoder
			2 LTSM layers
	"""
	
	def __init__(self, args, text_dataset):
		"""
		Args:
				args: parameters of the model
				text_dataset: the dataset object
		"""
		print("Model creation...")
		
		self.text_data = text_dataset  # Keep a reference on the dataset
		self.args = args  # Keep track of the parameters of the model
		self.dtype = tf.float32
		
		# Placeholders
		self.encoder_inputs = None
		self.decoder_inputs = None  # Same that decoderTarget plus the <go>
		self.decoder_targets = None
		self.decoder_weights = None  # Adjust the learning to the target sentence size
		
		# Main operators
		self.loss_fct = None
		self.opt_op = None
		self.outputs = None  # Outputs of the network, list of probability for each words
		
		# Construct the graphs
		self.build_network()
	
	def build_network(self):
		""" Create the computational graph
		"""
		
		# TODO: Create name_scopes (for better graph visualisation)
		# TODO: Use buckets (better perfs)
		
		# Parameters of sampled softmax (needed for attention mechanism and a large vocabulary size)
		output_projection = None
		# Sampled softmax only makes sense if we sample less than vocabulary size.
		if 0 < self.args.softmax_samples < self.text_data.get_vocabulary_size():
			output_projection = ProjectionOp(
				(self.args.hidden_size, self.text_data.get_vocabulary_size()),
				scope='softmax_projection',
				dtype=self.dtype
			)
			
			def sampled_softmax(inputs, labels):
				labels = tf.reshape(labels, [-1, 1])  # Add one dimension (nb of true classes, here 1)
				
				# We need to compute the sampled_softmax_loss using 32bit floats to
				# avoid numerical instabilities.
				local_wt = tf.cast(tf.transpose(output_projection.W), tf.float32)
				local_b = tf.cast(output_projection.b, tf.float32)
				local_inputs = tf.cast(inputs, tf.float32)
				
				return tf.cast(
					tf.nn.sampled_softmax_loss(
						local_wt,  # Should have shape [num_classes, dim]
						local_b,
						local_inputs,
						labels,
						self.args.softmax_samples,  # The number of classes to randomly sample per batch
						self.text_data.get_vocabulary_size()),  # The number of classes
					self.dtype)
		
		# Creation of the rnn cell
		enco_deco_cell = tf.nn.rnn_cell.BasicLSTMCell(self.args.hidden_size,
																									state_is_tuple=True)  # Or GRUCell, LSTMCell(args.hidden_size)
		# enco_deco_cell = tf.nn.rnn_cell.DropoutWrapper(enco_deco_cell, input_keep_prob=1.0, output_keep_prob=1.0)  # TODO: Custom values (WARNING: No dropout when testing !!!)
		enco_deco_cell = tf.nn.rnn_cell.MultiRNNCell([enco_deco_cell] * self.args.num_layers, state_is_tuple=True)
		
		# Network input (placeholders)
		
		with tf.name_scope('placeholder_encoder'):
			self.encoder_inputs = [tf.placeholder(tf.int32, [None, ]) for _ in
														 range(self.args.max_length_enco)]  # Batch size * sequence length * input dim
		
		with tf.name_scope('placeholder_decoder'):
			self.decoder_inputs = [tf.placeholder(tf.int32, [None, ], name='inputs') for _ in
														 range(self.args.max_length_deco)]  # Same sentence length for input and output (Right ?)
			self.decoder_targets = [tf.placeholder(tf.int32, [None, ], name='targets') for _ in
															range(self.args.max_length_deco)]
			self.decoder_weights = [tf.placeholder(tf.float32, [None, ], name='weights') for _ in
															range(self.args.max_length_deco)]
		
		# Define the network
		# Here we use an embedding model, it takes integer as input and convert them into word vector for
		# better word representation
		decoder_outputs, states = tf.nn.seq2seq.embedding_rnn_seq2seq(
			self.encoder_inputs,  # List<[batch=?, inputDim=1]>, list of size args.maxLength
			self.decoder_inputs,  # For training, we force the correct output (feed_previous=False)
			enco_deco_cell,
			self.text_data.get_vocabulary_size(),
			self.text_data.get_vocabulary_size(),  # Both encoder and decoder have the same number of class
			embedding_size=self.args.embedding_size,  # Dimension of each word
			output_projection=output_projection.get_weights() if output_projection else None,
			feed_previous=bool(self.args.test)
			# When we test (self.args.test), we use previous output as next input (feed_previous)
		)
		
		# For testing only
		if self.args.test:
			if not output_projection:
				self.outputs = decoder_outputs
			else:
				self.outputs = [output_projection(output) for output in decoder_outputs]
				
				# TODO: Attach a summary to visualize the output
		
		# For training only
		else:
			# Finally, we define the loss function
			self.loss_fct = tf.nn.seq2seq.sequence_loss(
				decoder_outputs,
				self.decoder_targets,
				self.decoder_weights,
				self.text_data.get_vocabulary_size(),
				softmax_loss_function=sampled_softmax if output_projection else None  # If None, use default SoftMax
			)
			tf.scalar_summary('loss', self.loss_fct)  # Keep track of the cost
			
			# Initialize the optimizer
			opt = tf.train.AdamOptimizer(
				learning_rate=self.args.learning_rate,
				beta1=0.9,
				beta2=0.999,
				epsilon=1e-08
			)
			self.opt_op = opt.minimize(self.loss_fct)
	
	def step(self, batch):
		""" Forward/training step operation.
		Does not perform run on itself but just return the operators to do so. Those have then to be run.
		Args:
				batch (Batch): Input data on testing mode, input and target on output mode
		Return:
				(ops), dict: A tuple of the (training, loss) operators or (outputs,) in testing mode with the associated feed dictionary
		"""
		
		# Feed the dictionary
		feed_dict = {}
		ops = None
		
		if not self.args.test:  # Training
			for i in range(self.args.max_length_enco):
				feed_dict[self.encoder_inputs[i]] = batch.encoder_seqs[i]
			for i in range(self.args.max_length_deco):
				feed_dict[self.decoder_inputs[i]] = batch.decoder_seqs[i]
				feed_dict[self.decoder_targets[i]] = batch.target_seqs[i]
				feed_dict[self.decoder_weights[i]] = batch.weights[i]
			
			ops = (self.opt_op, self.loss_fct)
		else:  # Testing (batchSize == 1)
			for i in range(self.args.max_length_enco):
				feed_dict[self.encoder_inputs[i]] = batch.encoder_seqs[i]
			feed_dict[self.decoder_inputs[0]] = [self.text_data.go_token]
			
			ops = (self.outputs,)
		
		# Return one pass operator
		return ops, feed_dict
