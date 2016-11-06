from jarvis.jobs import schedule_job  # need this to reschedule our job
import datetime
from random import randint
from jarvis.helpers.cache import cache
from jarvis.actions.outreach import fun_fact

def options():
	return {
		'trigger': 'date',
		'run_date': random_runtime(),
		'id': 'outreach'
	}


def random_runtime():
	now = datetime.datetime.now()
	
	# Get random time delta for next outreach
	# run_time = now + datetime.timedelta(hours=random_hour(), minutes=random_minute())
	run_time = now + datetime.timedelta(hours=0, minutes=1)

	# Check to make sure this new outreach time won't interfere with sleep time
	if during_sleep_time(run_time):
		run_time = push_until_morning(run_time)
	
	# Log how long we can expect to wait until the next outreach
	log_delta(run_time, now)
	
	return run_time


def log_delta(run_time, now):
	hour_delta = run_time.hour - now.hour
	min_delta = run_time.minute - now.minute

	if hour_delta < 0:
		hour_delta = run_time.hour + (24 - now.hour)
	
	if min_delta < 0:
		min_delta = run_time.minute + (60 - now.minute)
		hour_delta -= 1
		
	h = [hour_delta, 'hours']
	m = [min_delta, 'minutes']
	
	if min_delta in [0, 60]:
		m = []
		
		if min_delta == 60:
			h[0] += 1
	
	elif min_delta == 1:
		m[1] = 'minute'
	
	if h[0] == 1:
		h[1] = 'hour'
	
	if m: m[0] = str(m[0])
	h[0] = str(h[0])
	
	str_delta = ' '.join(h)
	
	if m:
		str_delta += ' and {}'.format(' '.join(m))
	
	print 'Scheduling next outreach for {} from now.'.format(str_delta)


def random_hour():
	# for now, just keep the outreach between 1 and 4 hour intervals
	return randint(1, 4)
	
	
def random_minute():
	return randint(0, 60)


def during_sleep_time(run_time):
	bed_hour, wake_hour = sleep_hours()
	return bed_hour < run_time.hour < wake_hour


def sleep_hours():
	return 1, 9


def push_until_morning(run_time):
	hours_until_morning = sleep_hours()[1] - run_time.hour
	return run_time + datetime.timedelta(hours=hours_until_morning)


def perform(app):
	with app.test_request_context():
		# Get current user's socket session id from Redis
		sid = cache.get('user_sid')
		
		if sid:
			fun_fact(sid)
		
	schedule_job(app, perform, options())
