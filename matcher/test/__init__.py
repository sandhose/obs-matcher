from flask import Flask, request

from flask_injector import FlaskInjector
from flask_sqlalchemy import SQLAlchemy
from flask_testing import TestCase as BaseTestCase
from matcher.app import db, setup_routes
from matcher.scheme import Base


class TestCase(BaseTestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config.from_object('matcher.config.TestConfig')

        db.init_app(app)

        setup_routes(app, admin=False)

        def configure(binder):
            binder.bind(
                SQLAlchemy,
                to=db,
                scope=request,
            )

        flask_injector = FlaskInjector(app=app, modules=[configure])

        flask_injector.injector.install_into(self, _internal=True)

        return app

    def setUp(self):
        Base.metadata.create_all(bind=db.engine)

    def tearDown(self):
        db.session.remove()
        table_names = [table.name for table in
                       reversed(Base.metadata.sorted_tables)]
        db.session.execute('TRUNCATE TABLE {}'.format(','.join(table_names)))
        db.session.commit()
