from trainer import Trainer


class Rnn:
	
	def __init__(self):
		self.trainer = Trainer()
		self.trainer.prep_for_app_use()
	
	def predict(self, user_input):
		return self.trainer.daemon_predict(user_input)