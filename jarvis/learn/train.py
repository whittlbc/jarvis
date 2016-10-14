import numpy as np
from definitions import model_path
from jarvis import logger
import jarvis.learn.utils.data_prepper as dp
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer, TfidfTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.externals import joblib


def perform():
	# Create a new grid search classifier from a sci-kit pipeline
	model = GridSearchCV(pipeline(), gs_clf_params(), n_jobs=-1)
	
	# Get your training and testing sets of data with 50/50 split
	(train_data, train_targets), (test_data, test_targets) = dp.get_data()
	
	# Train your model
	model = model.fit(train_data, train_targets)
	
	# Test it's accuracy
	predictions = model.predict(test_data)
	
	# Display the model's accuracy
	logger.info("\nModel Accuracy: {}\n".format(np.mean(predictions == test_targets)))
	
	# Save the trained model to disk
	save_model(model)


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


def save_model(model):
	joblib.dump(model.best_estimator_, model_path)
