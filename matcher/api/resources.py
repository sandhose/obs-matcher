from celery import Celery
from flask_restplus import Resource
from flask_sqlalchemy import SQLAlchemy
from injector import inject


class InjectedResource(Resource):
    """A resource that has the db and celery injected"""

    @inject
    def __init__(self, *args, db: SQLAlchemy, celery: Celery, **kwargs):
        super(InjectedResource, self).__init__(*args, **kwargs)
        self.db = db
        self.celery = celery

    @property
    def session(self):
        return self.db.session

    @property
    def query(self):
        return self.session.query
