import pandas
import glob
from jinja2 import Environment, FileSystemLoader
from definitions import data_path


def render_temp(file, **kwargs):
	env = Environment(loader = FileSystemLoader('templates'))
	template = env.get_template(file)
	return template.render(**kwargs)


def get_actions():
	actions = []
	
	for csv in csvs():
		action = read_csv(csv).values[:, 1][0]
		actions.append(action)
		
	actions.sort()
	return actions
	

def csvs():
	return glob.glob(data_path + "/*.csv")


def read_csv(f, sep='|'):
	return pandas.read_csv(f, sep=sep, header=None)
