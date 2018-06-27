from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from injector import inject


class DbMixin(object):
    """A class that has the db injected"""

    @inject
    def __init__(self, *args, db: SQLAlchemy, **kwargs):
        super(DbMixin, self).__init__(*args, **kwargs)
        self.db = db

    @property
    def session(self):
        return self.db.session

    @property
    def query(self):
        return self.session.query


class CeleryMixin(object):
    """A class that has celery injected"""

    @inject
    def __init__(self, *args, celery: Celery, **kwargs):
        super(CeleryMixin, self).__init__(*args, **kwargs)
        self.celery = celery
