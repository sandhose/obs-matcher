import contextlib
import logging
import os

from alembic.migration import MigrationContext
from celery import Celery, Task
from celery.signals import task_postrun
from celery_once import QueueOnce
from flask import Flask
from flask.cli import FlaskGroup
from flask_debugtoolbar import DebugToolbarExtension
from flask_injector import FlaskInjector
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from injector import Injector, Module, provider, singleton
from raven.contrib.celery import register_logger_signal, register_signal
from raven.contrib.flask import Sentry

from .commands import setup_cli
from .filters import register as register_filters
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
        celery.conf.ONCE = {
            'backend': 'celery_once.backends.Redis',
            'settings': {
                'url': app.config['CELERY_RESULT_BACKEND'],
                'default_timeout': 60 * 60
            }
        }

        class ContextTask(Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        class OnceTask(QueueOnce):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        celery.OnceTask = OnceTask

        def handle_celery_postrun(retval=None, *args, **kwargs):
            """After each Celery task, teardown our db session"""
            if app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN']:
                if not isinstance(retval, Exception):
                    db.session.commit()
            # If we aren't in an eager request (i.e. Flask will perform teardown), then teardown
            if not app.config['CELERY_ALWAYS_EAGER']:
                db.session.remove()

        task_postrun.connect(handle_celery_postrun)

        return celery


class SentryModule(Module):
    @provider
    @singleton
    def provide_sentry(self, app: Flask, celery: Celery) -> Sentry:
        sentry = Sentry(app=app, logging=True, level=logging.ERROR)

        register_logger_signal(sentry.client)
        register_signal(sentry.client)

        return sentry


def _setup_admin(app):
    from .admin import setup_admin
    setup_admin(app)


def setup_routes(app, admin=True):
    from .api import blueprint as api
    from .dashboard import blueprint as dashboard

    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(dashboard, url_prefix='/')

    if admin:
        # Do not install admin if upgrades are pending
        with contextlib.closing(db.engine.connect()) as con:
            migration_context = MigrationContext.configure(con)
            revision = migration_context.get_current_revision()
            heads = migration_context.get_current_heads()

            if revision in heads:
                _setup_admin(app)


def create_app(info=None):
    app = Flask('matcher', instance_relative_config=True)
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)

    # Load config using environment variable
    app.config.from_object('matcher.config.Config')
    app.config.from_pyfile('application.cfg', silent=True)
    app.url_map.strict_slashes = False  # Trailing slashes are not required
    db.init_app(app)

    app.jinja_env.add_extension('jinja2.ext.do')
    register_filters(app)

    DebugToolbarExtension(app=app)
    Migrate(app=app, db=db, directory=os.path.join(os.path.dirname(__file__),
                                                   'migrations'))

    setup_cli(app)
    with app.app_context():
        db.engine.pool._use_threadlocal = True
        setup_routes(app)

    FlaskInjector(injector=injector, app=app, modules=[SQLAlchemyModule, CeleryModule, SentryModule])
    injector.get(Sentry)

    return app


cli = FlaskGroup(create_app=create_app)
