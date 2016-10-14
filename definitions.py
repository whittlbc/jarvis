import os

basedir = os.path.abspath(os.path.dirname(__file__))
formulas_dir = basedir + '/jarvis/formulas'
model_path = basedir + '/jarvis/learn/model.pkl'
data_path = basedir + '/data'
default_speech_file = basedir + '/tmp/speech.ogg'
s3_speech_path = 'jarvis/speech.ogg'
