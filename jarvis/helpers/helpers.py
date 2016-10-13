import pandas
from jinja2 import Environment, FileSystemLoader
from definitions import train_csv


def render_temp(file, **kwargs):
	env = Environment(loader = FileSystemLoader('templates'))
	template = env.get_template(file)
	return template.render(**kwargs)


def get_actions():
	return uniq_list(pandas.read_csv(train_csv, sep='|').values[:, 1])


# preserves order
def uniq_list(list):
	seen = set()
	seen_add = seen.add
	return [x for x in list if not (x in seen or seen_add(x))]