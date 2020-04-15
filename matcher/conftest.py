import pytest
from flask import Flask, request
from flask_injector import FlaskInjector
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

from matcher.app import db as _db
from matcher.app import setup_routes
from matcher.filters import register as register_filters
from matcher.scheme import Base


@pytest.fixture(scope="session")
def app():
    """The flask app"""
    app = Flask(__name__)
    app.config.from_object("matcher.config.TestConfig")

    _db.init_app(app)

    app.jinja_env.add_extension("jinja2.ext.do")
    register_filters(app)

    setup_routes(app, admin=False)

    def configure(binder):
        binder.bind(SQLAlchemy, to=_db, scope=request)

    FlaskInjector(app=app, modules=[configure])

    with app.app_context():
        _db.engine.execute(text("CREATE EXTENSION IF NOT EXISTS tablefunc"))
        Base.metadata.create_all(bind=_db.engine, checkfirst=True)

        yield app

        _db.session.remove()

        Base.metadata.drop_all(bind=_db.engine)


@pytest.fixture(scope="function")
def db(app):
    _db.session.remove()
    table_names = [
        table.name
        for table in reversed(Base.metadata.sorted_tables)
        if not table.name.startswith("vw_")
    ]
    _db.session.execute("TRUNCATE TABLE {}".format(",".join(table_names)))
    _db.session.commit()
    return _db


@pytest.fixture(scope="function")
def session(db):
    return db.session


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()
