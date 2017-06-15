from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
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

admin = Admin(app)


def setup():
    from .scheme import Platform, PlatformGroup, Scrap, Value, \
        ValueID, ValueSource, ObjectLink, ObjectLinkWorkMeta, ExternalObject, \
        Person, AVWork, Movie, Episode, Season, Serie

    from .api import setup_api

    setup_api(app)

    admin.add_view(ModelView(Platform, db.session, name='Platform',
                             category='Platforms'))
    admin.add_view(ModelView(PlatformGroup, db.session, name='Group',
                             category='Platforms'))
    admin.add_view(ModelView(Scrap, db.session, name='Scrap',
                             category='Platforms'))
    admin.add_view(ModelView(Value, db.session, name='Value',
                             category='Values'))
    admin.add_view(ModelView(ValueID, db.session, name='ValueID',
                             category='Values'))
    admin.add_view(ModelView(ValueSource, db.session, name='Source',
                             category='Values'))
    admin.add_view(ModelView(ObjectLink, db.session))
    admin.add_view(ModelView(ObjectLinkWorkMeta, db.session))
    admin.add_view(ModelView(ExternalObject, db.session))
    admin.add_view(ModelView(Person, db.session))
    admin.add_view(ModelView(AVWork, db.session, name='AVWork',
                             category='Works'))
    admin.add_view(ModelView(Movie, db.session, name='Movie',
                             category='Works'))
    admin.add_view(ModelView(Episode, db.session, name='Episode',
                             category='Works'))
    admin.add_view(ModelView(Season, db.session, name='Season',
                             category='Works'))
    admin.add_view(ModelView(Serie, db.session, name='Serie',
                             category='Works'))

setup()

