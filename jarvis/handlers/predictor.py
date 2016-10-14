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
		
		# How confident is Jarvis that this is the answer?
		confidence = max(self.predictor.predict_proba(cleaned_input)[0])
		
		# Return None if confidence isn't good enough
		if not confidence >= 0.5: return None
		
		# Return the predicted action
		return self.actions[target_index]
