import os
import contextlib
from flask import Flask, url_for, render_template
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy


app = Flask('matcher')

env = os.environ.get('OBS_ENV', 'development')
app.config.from_object('matcher.config.{}Config'.format(env.title()))

db = SQLAlchemy(app)

migrate = Migrate(app=app, db=db,
                  directory=os.path.join(os.path.dirname(__file__),
                                         'migrations'))

manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def list_routes():
    from urllib.parse import unquote
    output = []
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(rule.methods)
        url = url_for(rule.endpoint, **options)
        line = unquote("{:35s} {:35s} {}".format(rule.endpoint, methods, url))
        output.append(line)

    for line in sorted(output):
        print(line)


@manager.command
def nuke():
    with contextlib.closing(db.engine.connect()) as con:
        trans = con.begin()
        for table in reversed(db.metadata.sorted_tables):
            if table.name != 'platform':
                con.execute(table.delete())
        trans.commit()


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
