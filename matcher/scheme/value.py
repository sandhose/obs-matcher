import re
from functools import partial

from sqlalchemy import (Column, Enum, ForeignKey, Integer, Sequence, Text,
                        func, select,)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from . import Base
from ..countries import lookup
from .platform import Platform
from .utils import CustomEnum


class ValueType(CustomEnum):
    TITLE = 1
    DATE = 2
    GENRES = 3
    DURATION = 4
    NAME = 5
    COUNTRY = 6

    def fmt(self, value):
        def m(r, t):
            result = re.match(r, t)
            return result.group(1) if result is not None else None

        duration_regex = r'^[^\d]*(\d+(?:.\d*)?)[^\d]*$'
        date_regex = r'(\d{4})'
        parenthesis_regex = r'\([^)]*\)'
        fmt_map = {
            ValueType.DURATION: partial(m, duration_regex),
            ValueType.COUNTRY: lookup,
            ValueType.DATE: partial(m, date_regex),
            ValueType.TITLE: lambda t: re.sub(parenthesis_regex, '', t).strip()
        }

        return fmt_map.get(self, lambda _: None)(value)


class Value(Base):
    __tablename__ = 'value'

    value_id_seq = Sequence('value_id_seq', metadata=Base.metadata)
    id = Column(Integer,
                value_id_seq,
                server_default=value_id_seq.next_value(),
                primary_key=True)
    type = Column(Enum(ValueType, name='value_type'), nullable=False)
    external_object_id = Column(Integer,
                                ForeignKey('external_object.id'),
                                nullable=False)
    text = Column(Text, nullable=False)

    external_object = relationship('ExternalObject',
                                   back_populates='values')
    sources = relationship('ValueSource',
                           back_populates='value',
                           cascade='all, delete-orphan')

    @hybrid_property
    def score(self):
        return sum(source.score for source in self.sources)

    @score.expression
    def score(cls):
        return select([func.sum(ValueSource.score)]).\
            where(ValueSource.value_id == cls.id).\
            label('total_score')

    def __repr__(self):
        return '<Value "{}">'.format(self.text)

    def __str__(self):
        return '{}({}): {}'.format(self.type, self.score, self.text)


class ValueSource(Base):
    __tablename__ = 'value_source'

    value_id = Column(Integer,
                      ForeignKey('value.id'),
                      primary_key=True)
    platform_id = Column(Integer,
                         ForeignKey('platform.id'),
                         primary_key=True)
    score_factor = Column(Integer,
                          nullable=False,
                          default=100)
    comment = Column(Text)

    value = relationship('Value', back_populates='sources')
    platform = relationship('Platform')

    @hybrid_property
    def score(self):
        return self.platform.base_score * self.score_factor

    @score.expression
    def score(cls):
        return cls.score_factor * select([Platform.base_score]).\
            where(Platform.id == cls.platform_id)

    def __repr__(self):
        return '<ValueSource {!r} on {!r}>'.format(self.value.text,
                                                   self.platform.name)
