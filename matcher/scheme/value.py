from sqlalchemy import func, select
from sqlalchemy.ext.hybrid import hybrid_property

from ..app import db
from .mixins import ResourceMixin
from .platform import Platform
from .utils import CustomEnum


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
    type = db.Column(db.Enum(ValueType, name='value_type'), nullable=False)
    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    text = db.Column(db.Text, nullable=False)

    external_object = db.relationship('ExternalObject',
                                      back_populates='attributes')
    sources = db.relationship('ValueSource',
                              back_populates='value',
                              cascade='all, delete-orphan')

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
        return '{}({}): {}'.format(self.type, self.score, self.text)


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
    comment = db.Column(db.Text)

    value = db.relationship('Value', back_populates='sources')
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
