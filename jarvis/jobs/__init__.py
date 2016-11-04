import glob
from apscheduler.schedulers.background import BackgroundScheduler
import logging
logging.basicConfig()


# Get a background scheduler instance and start it
scheduler = BackgroundScheduler()
scheduler.start()


# Add a job to the scheduler
def schedule_job(app, method, options):
	scheduler.add_job(lambda: method(app), **options)


def add_jobs(app):
	# Get a list of all our job file names
	file_names = [f.split('/')[-1][:-3] for f in glob.glob('jarvis/jobs/*.py') if f != 'jarvis/jobs/__init__.py']
	
	# Add each of our jobs to our scheduler
	for name in file_names:
		# import module from filename
		module = __import__('jarvis.jobs.{}'.format(name), globals(), locals(), ['object'], -1)
		
		# from module, get the perform method and options for the job
		method = getattr(module, 'perform')
		options = getattr(module, 'options')()
		
		# add our job to the scheduler
		schedule_job(app, method, options)

