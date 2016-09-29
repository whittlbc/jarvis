from jarvis import app
from jinja2 import Environment, FileSystemLoader


def registered_formulas():
	app.redis.hgetall('formulas')
	

def register_formula(formula):
	app.redis.hset('formulas', formula['pattern'], formula)


def render_temp(file, **kwargs):
	env = Environment(loader = FileSystemLoader('templates'))
	template = env.get_template(file)
	return template.render(**kwargs)
