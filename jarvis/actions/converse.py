from abstract_action import AbstractAction


class Converse(AbstractAction):
		
	def greet(self):
		given_name = self.params.get('given_name')
		
		# if no given name provided or specifically addressing the bot, respond.
		if not given_name or given_name.lower() == self.user.botname.lower():
			return self.respond('Hey {}!'.format(self.user.name))
		
		return None
		
	def morning(self):
		given_name = self.params.get('given_name')
		
		# if no given name provided or specifically addressing the bot, respond.
		if not given_name or given_name.lower() == self.user.botname.lower():
			return self.respond('Good Morning!')
		
		return None