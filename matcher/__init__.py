from flask import Flask, url_for
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

app.config.from_object('matcher.config')
# app.config.from_envvar('MATCHER_SETTINGS')

db = SQLAlchemy(app)

migrate = Migrate(app, db)

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


def setup():
    from .api import api
    from .admin import admin

    admin.init_app(app, endpoint='admin', url='/admin')
    app.register_blueprint(api, url_prefix='/api')


setup()
