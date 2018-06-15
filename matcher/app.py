import contextlib
import logging
import os

from flask import Flask, jsonify, render_template, request, url_for
from flask.cli import FlaskGroup
from raven.contrib.flask import Sentry

from alembic.migration import MigrationContext
from flask_debugtoolbar import DebugToolbarExtension
from flask_injector import FlaskInjector
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from injector import Module, provider, singleton

from .commands import setup_cli

l = logging.getLogger('injector')
l.setLevel(logging.DEBUG)
l.addHandler(logging.StreamHandler())

l = logging.getLogger('flask_restplus.api')
l.setLevel(logging.DEBUG)
l.addHandler(logging.StreamHandler())



db = SQLAlchemy()


def _setup_admin(app):
    from .admin import setup_admin
    setup_admin(app)


def setup_routes(app):
    from .api_old import api
    from .api import blueprint as api2

    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(api2, url_prefix='/api2')

    # Do not install admin if upgrades are pending
    with contextlib.closing(db.engine.connect()) as con:
        migration_context = MigrationContext.configure(con)
        revision = migration_context.get_current_revision()
        heads = migration_context.get_current_heads()

        if revision in heads:
            _setup_admin(app)

    @app.route('/queue', methods=['POST'])
    def queue(db: SQLAlchemy):
        from matcher.scheme.platform import Scrap
        from matcher.tasks.object import insert_dict

        scrap_id = request.headers.get('x-scrap-id', None)
        if scrap_id is None:
            raise Exception('Missing `x-scrap-id` header')
        scrap_id = int(scrap_id)

        assert db.session.query(Scrap).get(scrap_id)

        insert_dict.delay(request.json, scrap_id)
        return jsonify({'status': 'queued'})

    @app.route('/')
    def index():
        return render_template('index.html', navigation=[
            {'url': url_for('admin.index'), 'caption': 'Admin'},
            {'url': url_for('api.index'), 'caption': 'API'},
        ])


def configure(binder):
    binder.bind(
        SQLAlchemy,
        to=db,
        scope=request,
    )


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

    flask_injector = FlaskInjector(app=app, modules=[configure])

    return app


cli = FlaskGroup(create_app=create_app)
