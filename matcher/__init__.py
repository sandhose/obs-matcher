from flask import url_for, render_template
from flask_migrate import MigrateCommand
from flask_script import Manager

from .app import app, db
from .commands import RoutesCommand, NukeCommand
from .api import api
from .admin import admin

manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('routes', RoutesCommand(app))
manager.add_command('nuke', NukeCommand(db))

admin.init_app(app, endpoint='admin', url='/admin')
app.register_blueprint(api, url_prefix='/api')


@app.route('/')
def index():
    return render_template('index.html', navigation=[
        {'url': url_for('admin.index'), 'caption': 'Admin'},
        {'url': url_for('api.index'), 'caption': 'API'},
    ])
