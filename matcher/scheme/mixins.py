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


class ResourceMixin(object):
    @classmethod
    def register_api(cls, app, prefix, resource):
        cls.api_prefix = prefix
        resource.add_url_rules(app, rule_prefix=cls.prefix())

    @classmethod
    def prefix(cls):
        return '/api/{}'.format(cls.api_prefix)

    @property
    def self_link(self):
        return '{}{}/'.format(self.__class__.prefix(), self.id)
