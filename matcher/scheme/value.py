from sqlalchemy import Column, String, Sequence, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .utils import Base


class ValueID(Base):
    __tablename__ = 'value_id'

    id = Column(Integer, Sequence('value_id_id_seq'), primary_key=True)

    values = relationship('Value', back_populates='value_id')


class Value(Base):
    __tablename__ = 'value'

    id = Column(Integer, Sequence('value_id_seq'), primary_key=True)
    value_id_id = Column(Integer, ForeignKey('value_id.id'), nullable=False)
    text = Column(String, nullable=False)

    value_id = relationship('ValueID', back_populates='values')
    sources = relationship('Platform', secondary='value_source',
                           back_populates='values')


class ValueSource(Base):
    __tablename__ = 'value_source'

    id_value = Column(Integer, ForeignKey('value.id'), primary_key=True)
    id_platform = Column(Integer, ForeignKey('platform.id'), primary_key=True)
    score_factor = Column(Integer, nullable=False, default=100)
