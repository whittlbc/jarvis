import logging


def get_logger(app):
	app.logger.addHandler(logging.FileHandler('main.log'))
	app.logger.setLevel(logging.INFO)
	return app.logger
