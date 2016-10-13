import numpy as np
from definitions import model_path, basedir
from jarvis import logger
from jarvis.learn.utils.dataset import Dataset
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.externals import joblib


def perform(test=True):
	# Create a new grid search classifier from a sci-kit pipeline
	gs_clf = GridSearchCV(pipeline(), gs_clf_params(), n_jobs=-1)
	
	# Train your classifier
	train_set, gs_clf = train_model(gs_clf)
	
	# Test your classifier and log the results unless specifically told not to.
	if test: test_model(gs_clf)
	
	# Save the trained classifier to disk
	save_model(gs_clf)


def pipeline():
	return Pipeline([
		('vect', CountVectorizer()),
		('tfidf', TfidfTransformer()),
		('clf', SGDClassifier(loss='hinge', penalty='l2', alpha=1e-3, n_iter=5, shuffle=False)),
	])
	

def gs_clf_params():
	return {
		'vect__ngram_range': [(1, 1), (1, 2)],
		'tfidf__use_idf': (True, False),
		'clf__alpha': (1e-2, 1e-3)
	}


def train_model(model):
	train_set = Dataset(csv=csv_path('train/train.csv'))
	model = model.fit(train_set.data, train_set.targets)
	return [train_set, model]
	
	
def test_model(model):
	test_set = Dataset(csv=csv_path('test/test.csv'))
	predictions = model.predict(test_set.data)
	logger.info("\nModel Accuracy: {}\n".format(np.mean(predictions == test_set.targets)))
	

def save_model(model):
	joblib.dump(model.best_estimator_, model_path)


def csv_path(path):
	return basedir + '/jarvis/learn/data/' + path