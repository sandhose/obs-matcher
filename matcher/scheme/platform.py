from sqlalchemy import Column, String, Sequence, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .utils import Base


class PlatformGroup(Base):
    __tablename__ = 'platform_group'

    id = Column(Integer, Sequence('platform_group_id_seq'), primary_key=True)
    name = Column(String, nullable=False)

    platforms = relationship('Platform', back_populates='group')


class Platform(Base):
    __tablename__ = 'platform'

    id = Column(Integer, Sequence('platform_id_seq'), primary_key=True)
    name = Column(String, nullable=False)
    group_id = Column(Integer, ForeignKey('platform_group.id'))
    url = Column(String)
    country = Column(String(2))
    max_rating = Column(Integer)
    base_score = Column(Integer, nullable=False)

    group = relationship('PlatformGroup', back_populates='platforms')
    scraps = relationship('Scrap', back_populates='platform')
    values = relationship('Value', secondary='value_source',
                          back_populates='sources')


class Scrap(Base):
    __tablename__ = 'scrap'

    id = Column(Integer, Sequence('scrap_id_seq'), primary_key=True)
    platform_id = Column(Integer, ForeignKey('platform.id'), nullable=False)
    date = Column(DateTime)

    platform = relationship('Platform', back_populates='scraps')
    links = relationship('ObjectLink', secondary='scrap_link',
                         back_populates='scraps')
