import os

basedir = os.path.abspath(os.path.dirname(__file__))

api_dir = basedir + '/jarvis/api'

classifier_model_path = basedir + '/jarvis/learn/classify/model.pkl'
classify_data_path = basedir + '/data/classify'

conversational_model_path = basedir + '/jarvis/learn/converse/model.pkl'
converse_data_path = basedir + '/data/converse'