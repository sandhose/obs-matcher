from sqlalchemy.ext.declarative import declared_attr
from matcher import db


def ExternalObjectMixin(type):
    class mxn(object):
        @declared_attr
        def external_object_id(cls):
            return db.Column(db.Integer,
                             db.ForeignKey('external_object.id'),
                             nullable=False)

        @declared_attr
        def external_object(cls):
            return db.relationship('ExternalObject',
                                   foreign_keys=[cls.external_object_id])

    return mxn
