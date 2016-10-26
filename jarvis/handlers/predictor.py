from sklearn.externals import joblib
from definitions import model_path
from jarvis.learn.utils.data_cleaner import DataCleaner
import jarvis.helpers.helpers as helpers


class Predictor:
	predictor = None
	
	def __init__(self):
		self.actions = helpers.get_actions()
		
	def load_model(self):
		self.predictor = self.predictor or joblib.load(model_path, 'r')
		
	def predict(self, input):
		# Clean the user's inputted text (comes back as an array: ex: ['what the weather'])
		cleaned_input = DataCleaner().clean([[input]])
		
		# Get the target index for the action predicted by our NN
		target_index = self.predictor.predict(cleaned_input)[0]
		
		confidence = max(self.predictor.decision_function(cleaned_input)[0])
		
		print "Confidence: {}".format(confidence)
	
		return self.actions[target_index], confidence > 0.25
