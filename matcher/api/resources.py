from injector import inject
from celery import Celery
from flask_restplus import Resource
from flask_sqlalchemy import SQLAlchemy


class DbResource(Resource):
    """A resource that has the db injected"""

    @inject
    def __init__(self, *args, db: SQLAlchemy, **kwargs):
        super(DbResource, self).__init__(*args, **kwargs)
        self.db = db

    @property
    def session(self):
        return self.db.session

    @property
    def query(self):
        return self.session.query


class CeleryResource(Resource):
    """A resource that has celery injected"""

    @inject
    def __init__(self, *args, celery: Celery, **kwargs):
        super(CeleryResource, self).__init__(*args, **kwargs)
        self.celery = celery
