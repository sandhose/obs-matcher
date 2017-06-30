import enum
from flask import url_for
from sqlalchemy.ext.declarative import declared_attr
from matcher import db
from ..api.index import IndexView


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
        app.add_url_rule('/{}/<pk>/'.format(prefix),
                         endpoint='{}_detail'.format(prefix),
                         view_func=resource.as_detail(),
                         methods=['GET', 'POST', 'PUT', 'DELETE'])

        app.add_url_rule('/{}/'.format(prefix),
                         endpoint='{}_list'.format(prefix),
                         view_func=resource.as_list(),
                         methods=['GET', 'POST', 'PUT', 'DELETE'])
        IndexView.register_api(prefix, 'api.{}_list'.format(prefix))

    @property
    def self_link(self):
        return url_for('api.{}_detail'.format(self.__class__.api_prefix),
                       pk=self.id, _external=True)


class CustomEnum(enum.Enum):
    def __str__(self):
        return self.name.lower()

    @classmethod
    def from_name(cls, name):
        return getattr(cls, name.upper(), None)
