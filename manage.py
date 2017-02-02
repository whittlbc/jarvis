from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from jarvis import app, db
from jarvis.helpers.configs import config

app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URL')

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
	manager.run()