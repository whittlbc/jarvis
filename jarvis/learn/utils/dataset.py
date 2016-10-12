import pandas
from data_cleaner import DataCleaner


class Dataset:
	
	def __init__(self, csv='', sep='|'):
		self.csv = csv
		self.sep = sep
		self.data, self.targets, self.target_names = self.process_data()
	
	def process_data(self):
		# Import the dataset from CSV
		dataset = self.import_data_from_csv()
		
		# Separate the inputs from the outputs (targets)
		inputs = dataset[:, 0:1]
		target_list = dataset[:, 1]
		
		# Clean the data
		cleaned_data = DataCleaner().clean(inputs)
		
		# Format targets into an array of integers corresponding
		# to the unique index of that target name
		targets, target_names = self.format_targets(target_list)
		
		return [cleaned_data, targets, target_names]
	
	def import_data_from_csv(self):
		return pandas.read_csv(self.csv, sep=self.sep).values
	
	def format_targets(self, target_list):
		target_map = {}
		targets = []
		target_names = []
		
		for target in target_list:
			if target not in target_map:
				target_map[target] = len(target_map.keys())
				target_names.append(target)
			
			targets.append(target_map[target])
		
		return targets, target_names
