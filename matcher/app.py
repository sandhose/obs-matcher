import contextlib
import logging
import os

from alembic.migration import MigrationContext
from flask import Flask, render_template, url_for
from flask.cli import FlaskGroup
from flask_debugtoolbar import DebugToolbarExtension
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from raven.contrib.flask import Sentry

from .commands import setup_cli

db = SQLAlchemy()
sentry = Sentry()
toolbar = DebugToolbarExtension()


def setup_routes(app):
    from .api import api
    from .admin import setup_admin

    app.register_blueprint(api, url_prefix='/api')

    # Do not install admin if upgrades are pending
    with contextlib.closing(db.engine.connect()) as con:
        migration_context = MigrationContext.configure(con)
        revision = migration_context.get_current_revision()
        heads = migration_context.get_current_heads()

        if revision in heads:
            setup_admin(app)

    @app.route('/')
    def index():
        return render_template('index.html', navigation=[
            {'url': url_for('admin.index'), 'caption': 'Admin'},
            {'url': url_for('api.index'), 'caption': 'API'},
        ])


def create_app(info=None):
    app = Flask('matcher', instance_relative_config=True)

    # Load config using environment variable
    app.config.from_object('matcher.config.Config')
    app.config.from_pyfile('application.cfg', silent=True)
    sentry.init_app(app, logging=True, level=logging.ERROR)
    db.init_app(app)
    toolbar.init_app(app)

    Migrate(app=app, db=db,
            directory=os.path.join(os.path.dirname(__file__),
                                   'migrations'))

    setup_cli(app)
    with app.app_context():
        setup_routes(app)

    return app


cli = FlaskGroup(create_app=create_app)
