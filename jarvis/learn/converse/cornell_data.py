from io import open


class CornellData:
	def __init__(self, dir_name):
		"""
		Args:
				dir_name (string): directory where to load the corpus
		"""
		self.lines = {}
		self.conversations = []
		
		MOVIE_LINES_FIELDS = ["lineID", "characterID", "movieID", "character", "text"]
		MOVIE_CONVERSATIONS_FIELDS = ["character1ID", "character2ID", "movieID", "utteranceIDs"]
		
		self.lines = self.load_lines(dir_name + "movie_lines.txt", MOVIE_LINES_FIELDS)
		self.conversations = self.load_conversations(dir_name + "movie_conversations.txt", MOVIE_CONVERSATIONS_FIELDS)
		
		# TODO: Cleaner program (merge copy-paste) !!
	
	def load_lines(self, file_name, fields):
		"""
		Args:
				file_name (str): file to load
				field (set<str>): fields to extract
		Return:
				dict<dict<str>>: the extracted fields for each line
		"""
		lines = {}
		
		with open(file_name, 'r', encoding='iso-8859-1') as f:  # TODO: Solve Iso encoding pb !
			for line in f:
				values = line.split(" +++$+++ ")
				
				# Extract fields
				line_obj = {}
				for i, field in enumerate(fields):
					line_obj[field] = values[i]
				
				lines[line_obj['lineID']] = line_obj
		
		return lines
	
	def load_conversations(self, file_name, fields):
		"""
		Args:
				file_name (str): file to load
				field (set<str>): fields to extract
		Return:
				dict<dict<str>>: the extracted fields for each line
		"""
		conversations = []
		
		with open(file_name, 'r', encoding='iso-8859-1') as f:  # TODO: Solve Iso encoding pb !
			for line in f:
				values = line.split(" +++$+++ ")
				
				# Extract fields
				conv_obj = {}
				for i, field in enumerate(fields):
					conv_obj[field] = values[i]
				
				line_ids = conv_obj["utteranceIDs"][2:-3].split("', '")
				
				# print(conv_obj["utteranceIDs"])
				# for line_id in line_ids:
				# print(line_id, end=' ')
				# print()
				
				# Reassemble lines
				conv_obj["lines"] = []
				for line_id in line_ids:
					conv_obj["lines"].append(self.lines[line_id])
				
				conversations.append(conv_obj)
		
		return conversations
	
	def getConversations(self):
		return self.conversations
