import pytest
from flask import Flask, request
from flask_injector import FlaskInjector
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from matcher.app import db as _db
from matcher.app import setup_routes
from matcher.scheme import Base


@pytest.fixture(scope="session")
def app():
    """The flask app"""
    app = Flask(__name__)
    app.config.from_object('matcher.config.TestConfig')

    _db.init_app(app)

    setup_routes(app)

    def configure(binder):
        binder.bind(
            SQLAlchemy,
            to=_db,
            scope=request,
        )

    FlaskInjector(app=app, modules=[configure])

    with app.app_context():
        _db.engine.execute(text('CREATE EXTENSION IF NOT EXISTS tablefunc'))
        Base.metadata.create_all(bind=_db.engine)

        yield app

        _db.session.remove()

        Base.metadata.drop_all(bind=_db.engine)


@pytest.fixture(scope="function")
def db(app):
    _db.session.remove()
    table_names = [table.name for table in
                   reversed(Base.metadata.sorted_tables)]
    _db.session.execute('TRUNCATE TABLE {}'.format(','.join(table_names)))
    _db.session.commit()
    return _db


@pytest.fixture(scope="function")
def session(db):
    return db.session


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()
