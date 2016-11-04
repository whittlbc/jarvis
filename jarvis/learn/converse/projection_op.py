import tensorflow as tf


# Single layer perceptron
# Project input tensor on the output dimension
class ProjectionOp:
	
	# Args:
	# 	shape: a tuple (input dim, output dim)
	# 	scope (str): encapsulate variables
	# 	dtype: the weights type
	def __init__(self, shape, scope=None, dtype=None):
		assert len(shape) == 2
		self.scope = scope
		
		# Projection on the keyboard.
		with tf.variable_scope('weights_' + self.scope):
			self.W = tf.get_variable('weights', shape, dtype=dtype)
			self.b = tf.get_variable('bias', shape[1], initializer=tf.constant_initializer(), dtype=dtype)
	
	# Project the output of the decoder into the vocabulary space
	# Args:
	# 	X (tf.Tensor): input value
	def __call__(self, X):
		with tf.name_scope(self.scope):
			return tf.matmul(X, self.W) + self.b

	# Convenience method for some tf arguments
	def get_weights(self):
		return self.W, self.b