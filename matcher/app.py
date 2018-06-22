import contextlib
import logging
import os

from alembic.migration import MigrationContext
from celery import Celery
from flask import Flask, render_template, url_for
from flask.cli import FlaskGroup
from flask_debugtoolbar import DebugToolbarExtension
from flask_injector import FlaskInjector
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from injector import Injector, Module, provider, singleton
from raven.contrib.flask import Sentry

from .commands import setup_cli
from .scheme import metadata

db = SQLAlchemy(metadata=metadata)

injector = Injector()


class SQLAlchemyModule(Module):
    @provider
    @singleton
    def provide_db(self, app: Flask) -> SQLAlchemy:
        return db


class CeleryModule(Module):
    @provider
    @singleton
    def provide_celery(self, app: Flask) -> Celery:
        celery = Celery(
            app.import_name,
            backend=app.config['CELERY_RESULT_BACKEND'],
            broker=app.config['CELERY_BROKER_URL'],
            imports=('matcher.tasks.object',)
        )
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        return celery


def _setup_admin(app):
    from .admin import setup_admin
    setup_admin(app)


def setup_routes(app, admin=True):
    from .api import blueprint as api

    app.register_blueprint(api, url_prefix='/api')

    if admin:
        # Do not install admin if upgrades are pending
        with contextlib.closing(db.engine.connect()) as con:
            migration_context = MigrationContext.configure(con)
            revision = migration_context.get_current_revision()
            heads = migration_context.get_current_heads()

            if revision in heads:
                _setup_admin(app)

    @app.route('/')
    def index():
        return render_template('index.html', navigation=[
            {'url': url_for('admin.index'), 'caption': 'Admin'},
            {'url': url_for('api.root'), 'caption': 'API'},
        ])


def create_app(info=None):
    app = Flask('matcher', instance_relative_config=True)

    # Load config using environment variable
    app.config.from_object('matcher.config.Config')
    app.config.from_pyfile('application.cfg', silent=True)
    db.init_app(app)

    DebugToolbarExtension(app=app)
    Sentry(app=app, logging=True, level=logging.ERROR)
    Migrate(app=app, db=db, directory=os.path.join(os.path.dirname(__file__),
                                                   'migrations'))

    setup_cli(app)
    with app.app_context():
        setup_routes(app)

    FlaskInjector(injector=injector, app=app, modules=[SQLAlchemyModule, CeleryModule])

    return app


cli = FlaskGroup(create_app=create_app)
