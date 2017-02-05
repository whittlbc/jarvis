from converse import Converse


action_map = {
	'input.greeting': (Converse, 'greet'),
	'input.good_morning': (Converse, 'morning')
}


def klass_method_for_action(action=''):
	return action_map.get(action)