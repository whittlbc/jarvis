from jinja2 import Environment, FileSystemLoader
from definitions import formulas_dir


def register_formula(filename, contents):
	file_path = formulas_dir + '/{}.py'.format(filename)
	f = open(file_path, 'a')
	f.write(contents)

# figure out if you wanna do it so that all of the formulas for the same "file" are shown at once on the frontend.
# if so, will need to change this to overwrite the contents of the file instead of appending. Appending
# should be done if you're doing it modularly. Figure out FE design first.
				

def render_temp(file, **kwargs):
	env = Environment(loader = FileSystemLoader('templates'))
	template = env.get_template(file)
	return template.render(**kwargs)
