import enum

from sqlalchemy import Column, Sequence, Integer, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship

from .utils import Base


class Gender(enum.Enum):
    not_known = 0
    male = 1
    female = 2
    not_applicable = 9


class Role(enum.Enum):
    director = 0
    actor = 1
    writer = 2


role = Table(
    'role', Base.metadata,
    Column('person_id', ForeignKey('Person'), primary_key=True),
    Column('av_work_id', ForeignKey('AVWork'), primary_key=True),
    Column('role', Enum(Role, name='role'))
)


class Person(Base):
    __tablename__ = 'person'

    id = Column(Integer, Sequence('person_id_seq'), primary_key=True)

    external_object_id = Column(Integer, ForeignKey('external_object.id'),
                                nullable=False)
    name_value_id = Column(Integer, ForeignKey('value_id.id'), nullable=False)

    external_object = relationship('ExternalObject',
                                   foreign_keys=[external_object_id])
    name = relationship('ValueID', foreign_keys=[name_value_id])
    gender = Column(Enum(Gender, name='gender'))
    roles = relationship('AVWork', back_populates='staffs', secondary='role')
