import pandas
from data_cleaner import DataCleaner
from jarvis.learn.utils.actions import actions


class Dataset:
	
	def __init__(self, csv='', sep='|'):
		self.csv = csv
		self.sep = sep
		self.data, self.targets = self.process_data()
	
	def process_data(self):
		# Import the dataset from CSV
		dataset = self.import_data_from_csv()
		
		# Separate the inputs from the outputs
		inputs = dataset[:, 0:1]
		outputs = dataset[:, 1]
		
		# Clean the data
		cleaned_data = DataCleaner().clean(inputs)
		
		# Format targets into an array of integers corresponding
		# to the unique index of that target name
		targets = self.format_targets(outputs)
		
		return [cleaned_data, targets]
	
	def import_data_from_csv(self):
		return pandas.read_csv(self.csv, sep=self.sep).values
	
	def format_targets(self, target_list):
		target_map = {}
		index = 0
		
		# Map targets to their index inside of actions array
		for action in actions:
			target_map[action] = index
			index += 1
		
		return map(lambda target: target_map[target], target_list)
