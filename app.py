from jarvis import app, helpers
from flask import jsonify, request
from flask.ext.socketio import SocketIO
from jarvis.event_handler import EventHandler
from jarvis import formulas

socket = SocketIO(app)

@app.route('/')
def index():
	return helpers.render_temp('index.html')


@app.route('/formula', methods = ['POST'])
def new_formula():
	formula_filename = request.args['formula_filename']
	formula_contents = request.args['formula_contents']
	
	helpers.register_formula(formula_filename, formula_contents)

	return jsonify({})


@socket.on('event', namespace = '/master')
def new_event(event):
	EventHandler(event).handle_event()
	

if __name__ == '__main__':
	socket.run(app, port = 3000, debug = app.config.get('DEBUG'))
