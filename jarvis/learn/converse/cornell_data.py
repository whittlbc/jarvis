from io import open


class CornellData:
	RESOURCE_INFO = {
		'lines': ['movie_lines.txt', ['lineID', 'characterID', 'movieID', 'character', 'text']],
		'conversations': ['movie_conversations.txt', ['character1ID', 'character2ID', 'movieID', 'utteranceIDs']]
	}
	
	def __init__(self, dir_name):
		self.dir_name = dir_name
		self.lines = self.load_resource(lines=True)
		self.conversations = self.load_resource(conversations=True)
	
	def load_resource(self, lines=False, conversations=False):
		if lines == conversations:
			print 'Cannot load resource: Both lines and conversations cannot be set to {}.'.format(lines)
			return
		
		if lines:
			resource_info = self.RESOURCE_INFO['lines']
			resources = {}
		else:
			resource_info = self.RESOURCE_INFO['conversations']
			resources = []
		
		file_name, fields = resource_info
		
		with open(self.dir_name + file_name, 'r', encoding='iso-8859-1') as f:
			for line in f:
				values = line.split(' +++$+++ ')
				resource = {}
				
				for i, field in enumerate(fields):
					resource[field] = values[i]
				
				if lines:
					resources[resource['lineID']] = resource
				else:
					line_ids = resource['utteranceIDs'][2:-3].split("', '")
					resource['lines'] = []
					
					for line_id in line_ids:
						resource['lines'].append(self.lines[line_id])
					
					resources.append(resource)
		
		return resources
	
	def get_conversations(self):
		return self.conversations