import numpy as np
import jarvis.helpers.helpers as helpers
from data_cleaner import DataCleaner


def get_data(csv=None, sep='|'):
	dataset = create_dataset(csv, sep)
	
	inputs = DataCleaner().clean(dataset[:, 0:1])
	outputs = format_targets(dataset[:, 1])
	
	train_data, test_data = inputs[::2], inputs[1::2]
	train_targets, test_targets = outputs[::2], outputs[1::2]
	
	return [(train_data, train_targets), (test_data, test_targets)]


def create_dataset(csv, sep):
	if csv:
		return helpers.read_csv(csv, sep=sep).values
	else:
		data = []
		
		for f in helpers.csvs():
			for row in helpers.read_csv(f, sep=sep).values:
				data.append(list(row))
		
		return np.array(data)

	
def format_targets(target_list):
	target_map = {}
	index = 0
	actions = helpers.get_actions()
	
	# Map targets to their index inside of actions array
	for action in actions:
		target_map[action] = index
		index += 1
	
	return map(lambda target: target_map[target], target_list)
