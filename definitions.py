import os

basedir = os.path.abspath(os.path.dirname(__file__))

api_dir = basedir + '/jarvis/api'
formulas_dir = basedir + '/formulas'

classifier_model_path = basedir + '/jarvis/learn/classify/model.pkl'
classify_data_path = basedir + '/data/classify'

conversational_model_path = basedir + '/jarvis/learn/converse/model.pkl'
converse_data_path = basedir + '/data/converse'

cookie_name = 'JARVIS_COOKIE'
session_header = 'Jarvis-Api-Token'

formula_uploads_path = basedir + '/tmp/formulas'
formula_uploads_module = 'tmp.formulas'