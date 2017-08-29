import os
from flask import Flask, url_for, render_template
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy

from .commands import RoutesCommand, NukeCommand

app = Flask('matcher')

# Load config using environment variable
env = os.environ.get('OBS_ENV', 'development')
app.config.from_object('matcher.config.{}Config'.format(env.title()))

db = SQLAlchemy(app)

migrate = Migrate(app=app, db=db,
                  directory=os.path.join(os.path.dirname(__file__),
                                         'migrations'))

manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('routes', RoutesCommand(app))
manager.add_command('nuke', NukeCommand(db))


def setup():
    from .api import api
    from .admin import admin

    admin.init_app(app, endpoint='admin', url='/admin')
    app.register_blueprint(api, url_prefix='/api')

    @app.route('/')
    def index():
        return render_template('index.html', navigation=[
            {'url': url_for('admin.index'), 'caption': 'Admin'},
            {'url': url_for('api.index'), 'caption': 'API'},
        ])


setup()
