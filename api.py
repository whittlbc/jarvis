import os
from jarvis.helpers.helpers import to_slug
from definitions import api_dir
import argparse
parser = argparse.ArgumentParser()


def error(msg=''):
	raise BaseException(msg)
	

def global_options():
	return [
		{
			'arg': '--new',
			'options': {
				'action': 'store_true',
				'help': 'use to create a new api integration'
			}
		}
	]


def get_args():
	global_args = parser.add_argument_group('Global')

	for arg_info in global_options():
		global_args.add_argument(arg_info['arg'], **arg_info['options'])
	
	return parser.parse_args()


def until_correct(prompt='', valid_answers=None, incorrect_msg=None, ignore_case=True):
	valid_answers = valid_answers or []
	
	while True:
		response = raw_input(prompt).strip()
		
		if ignore_case:
			resp_to_test = response.lower()
			answers_to_test = [a.lower() for a in valid_answers]
		else:
			resp_to_test = response
			answers_to_test = valid_answers
		
		if resp_to_test in answers_to_test:
			return response
		else:
			if incorrect_msg:
				print incorrect_msg


def create_api_file(name, slug, is_wrapper_api=False):
	file_path = api_dir + '/{}.py'.format(slug)
	
	if os.path.isfile(file_path):
		print "API file already exists: {}\nSkipping...".format(file_path)
	
	if is_wrapper_api:
		contents = 'from jarvis.api.wrapper import Wrapper\n\n\n' \
							 'class {}(Wrapper):\n\n' \
							 '\tdef __init__(self):\n' \
							 '\t\tself.slug = __name__.split(\'.\').pop()\n' \
							 '\t\tWrapper.__init__(self, self.slug)'.format(name)
	else:
		contents = 'from jarvis.api.abstract_api import AbstractApi\n\n\n' \
							 'class {}(AbstractApi):\n\n' \
							 '\tdef __init__(self):\n' \
							 '\t\tself.slug = __name__.split(\'.\').pop()\n' \
							 '\t\tAbstractApi.__init__(self, self.slug)'.format(name)
		
	with open(file_path, 'w+') as f:
		f.write(contents)
		f.close()
		
		
def add_authed_instance_method(slug, lib):
	file_path = api_dir + '/authed_instances.py'
	new_func = "\n\n\ndef {}(configs):\n".format(slug)
	
	if lib:
		new_func += '\timport {}\n'.format(lib)
	else:
		new_func += '\t# TODO: import library you wish to wrap.'
	
	new_func += '\t# TODO: create and return an authed API class instance.'
	
	with open(file_path, 'a') as f:
		f.write(new_func)
		f.close()


def new_api():
	import jarvis.helpers.db as db
	
	# Ask user for name of API
	name = raw_input('API Name (Required): ').strip()
	
	if not name:
		error('API Name cannot be blank.')
		
	# Create slug from name
	slug = to_slug(name)
	
	# Make sure API doesn't already exist for slug.
	if db.service(slug):
		error('API already exists with a slug of: {}. Try again with a different name.'.format(slug))
		
	# Ask user to list out config vars associated with API
	configs = raw_input("Comma-separated API config vars (Optional): ")
	
	if configs:
		# Clean the configs and uppercase them
		configs = [c.strip().upper() for c in configs.split(',') if c.strip != '']
	else:
		configs = []
		
	# Get optional url info for the service
	api_url = raw_input('API URL (Optional): ').strip()
	home_url = raw_input('Home URL (Optional): ').strip()
	
	# Figure out if the API will be a "wrapper" api or no.
	wrapper_resp = until_correct(
		prompt="Will this API be wrapping an existing library? (y/n): ",
		valid_answers=['y', 'n', 'yes', 'no'],
		incorrect_msg="Please type 'y' or 'n'."
	)
	
	is_wrapper_api = wrapper_resp.lower() in ['y', 'yes']
	
	if is_wrapper_api:
		lib = raw_input('Which python library are you wrapping?: ').strip()
		
	new_service = {
		'service': name,
		'slug': slug,
		'configs': configs,
		'apiUrl': api_url,
		'homeUrl': home_url
	}
	
	print 'Adding {} to the DB as a service...'.format(name)
	
	# Create the new service record
	db.insert('services', new_service)
	
	print 'Creating jarvis.api.{}...'.format(slug)
	
	create_api_file(name, slug, is_wrapper_api=is_wrapper_api)
	
	if is_wrapper_api:
		print "Adding '{}' function to authed_instances.py...".format(slug)
		add_authed_instance_method(slug, lib)
		
		if lib:
			print 'Installing {} library...'.format(lib)
			os.system('pip install {}'.format(lib))
		
	print 'Added {} as an API integration!'.format(name)
	
	
def show_help():
	print parser.format_help()


def find_action_from_args(args):
	if args.new:
		return new_api
	else:
		return show_help


args = get_args()
action = find_action_from_args(args)
action()