from sqlalchemy.orm import object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, func
import restless.exceptions

from matcher import db
from .platform import Platform
from .object import ExternalObject, ExternalObjectType
from .mixins import ResourceMixin, CustomEnum


class ValueType(CustomEnum):
    TITLE = 1
    DATE = 2
    GENRES = 3
    DURATION = 4
    NAME = 5
    COUNTRY = 6


class Value(db.Model, ResourceMixin):
    __tablename__ = 'value'

    id = db.Column(db.Integer,
                   db.Sequence('value_id_seq'),
                   primary_key=True)
    type = db.Column(db.Enum(ValueType))
    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    text = db.Column(db.String, nullable=False)

    external_object = db.relationship('ExternalObject',
                                      back_populates='attributes')
    sources = db.relationship('Platform',
                              secondary='value_source',
                              back_populates='values')

    def __init__(self, external_object, type, text, sources=[]):
        if not isinstance(external_object, ExternalObject):
            try:
                external_object = ExternalObject.query.filter(
                    ExternalObject.id == external_object).one()
            except:
                raise restless.exceptions.NotFound()

        self.external_object = external_object

        if not isinstance(type, ValueType):
            type = ValueType.from_name(type)

        if type is None or text is None or str(text) == '':
            raise restless.exceptions.BadRequest()

        self.type = type
        self.text = text

        object_session(self).add(self)

        for source in sources:
            try:
                platform = source['platform']
            except:
                platform = source

            platform = Platform.resolve(platform)

            if platform is None:
                raise restless.exceptions.NotFound()

            if hasattr(source, 'score_factor'):
                score_factor = source['score_factor']
            else:
                score_factor = 100

            object_session(self).add(ValueSource(
                value=self,
                platform=platform,
                score_factor=score_factor
            ))

    def add_source(self, platform):
        existing = object_session(self).\
            query(ValueSource).\
            filter(ValueSource.value == self,
                   ValueSource.platform == platform).\
            first()

        if (not existing):
            object_session(self).add(ValueSource(value=self,
                                                 platform=platform))

    @hybrid_property
    def score(self):
        return sum(source.score for source in self.sources)

    @score.expression
    def score(cls):
        return select([func.sum(ValueSource.score)]).\
            where(ValueSource.id_value == cls.id).\
            label('total_score')

    def __repr__(self):
        return '<Value "{}">'.format(self.text)

    def __str__(self):
        return '{}: {}'.format(self.type, self.text)


class ValueSource(db.Model):
    __tablename__ = 'value_source'

    id_value = db.Column(db.Integer,
                         db.ForeignKey('value.id'),
                         primary_key=True)
    id_platform = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            primary_key=True)
    score_factor = db.Column(db.Integer,
                             nullable=False,
                             default=100)

    value = db.relationship('Value')
    platform = db.relationship('Platform')

    @hybrid_property
    def score(self):
        return self.platform.base_score * self.score_factor

    @score.expression
    def score(cls):
        return cls.score_factor * select([Platform.base_score]).\
            where(Platform.id == cls.id_platform)

    def __repr__(self):
        return '<ValueSource {!r} on {!r}>'.format(self.value.text,
                                                   self.platform.name)
