from injector import inject
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
