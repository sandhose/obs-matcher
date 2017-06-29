from flask import Flask
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


def setup():
    from .api import setup_api
    from .admin import setup_admin

    setup_api(app)
    setup_admin(app)


setup()
