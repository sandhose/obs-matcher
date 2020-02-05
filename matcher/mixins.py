from celery import Celery
from flask.views import View
from flask_sqlalchemy import SQLAlchemy
from injector import inject


class InjectedView(View):
    """A view that has the db and celery injected"""

    @inject
    def __init__(self, db: SQLAlchemy, celery: Celery):
        self.db = db
        self.celery = celery

    @property
    def session(self):
        return self.db.session

    @property
    def query(self):
        return self.session.query
