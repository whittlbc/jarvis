from jarvis import logger


def find_matching_formula(formula_uids, query=''):
	if not query: return None
	
	for uid in formula_uids:
		try:
			formula = __import__('formulas.{}'.format(uid), globals(), locals(), ['object'], -1)
		except ImportError as e:
			logger.error('Error importing formula by uid: {} with error: {}'.format(uid, e))
			return None
		
		if not hasattr(formula, 'Formula'):
			logger.error('formula module has no class, Formula, as an attribute.')
			return None
	
		formula_klass = formula.Formula
		
		if formula_klass.triggered(query):
			return formula_klass
	
	return None
