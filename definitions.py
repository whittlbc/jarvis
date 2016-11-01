import os

basedir = os.path.abspath(os.path.dirname(__file__))
formulas_dir = basedir + '/jarvis/formulas'
classifier_model_path = basedir + '/jarvis/learn/classify/model.pkl'
conversational_model_path = basedir + '/jarvis/learn/converse/model.pkl'
actions_data_path = basedir + '/data/actions'
actions_data_path = basedir + '/data/converse'
default_speech_file = basedir + '/tmp/speech.ogg'
s3_speech_path = 'jarvis/speech.ogg'