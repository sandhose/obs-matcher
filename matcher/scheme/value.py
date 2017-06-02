from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import select, func

from matcher import db
from .platform import Platform


class ValueID(db.Model):
    __tablename__ = 'value_id'

    id = db.Column(db.Integer, db.Sequence('value_id_id_seq'),
                   primary_key=True)

    values = db.relationship('Value',
                             order_by='Value.score',
                             back_populates='value_id')

    def __repr__(self):
        return '<ValueID {} {!r}>'.format(self.id, str(self.values[0]))


class Value(db.Model):
    __tablename__ = 'value'

    id = db.Column(db.Integer,
                   db.Sequence('value_id_seq'),
                   primary_key=True)
    value_id_id = db.Column(db.Integer,
                            db.ForeignKey('value_id.id'),
                            nullable=False)
    text = db.Column(db.String, nullable=False)

    value_id = db.relationship('ValueID',
                               back_populates='values')
    sources = db.relationship('Platform',
                              secondary='value_source',
                              back_populates='values')

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
        return self.text


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
