import enum

from sqlalchemy import Column, Sequence, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship

from .utils import Base


class AVWorkType(enum.Enum):
    movie = 1
    serie = 2


class AVWork(Base):
    __tablename__ = 'av_work'

    id = Column(Integer, Sequence('av_work_id_seq'), primary_key=True)

    external_object_id = Column(Integer, ForeignKey('external_object.id'),
                                nullable=False)
    title_value_id = Column(Integer, ForeignKey('value_id.id'),
                            nullable=False)
    date_value_id = Column(Integer, ForeignKey('value_id.id'),
                           nullable=False)
    duration_value_id = Column(Integer, ForeignKey('value_id.id'),
                               nullable=False)

    external_object = relationship('ExternalObject',
                                   foreign_keys=[external_object_id])
    title = relationship('ValueID', foreign_keys=[title_value_id])
    date = relationship('ValueID', foreign_keys=[date_value_id])
    type = Column(Enum(AVWorkType, name='avwork_type'))
    duration = relationship('ValueID', foreign_keys=[duration_value_id])
    staffs = relationship('Person', back_populates='roles', secondary='role')


class Movie(Base):
    __tablename__ = 'movie'

    id = Column(Integer, Sequence('movie_id_seq'), primary_key=True)
    av_work_id = Column(Integer, ForeignKey('av_work.id'), nullable=False)
    country_value_id = Column(Integer, ForeignKey('value_id.id'),
                              nullable=False)
    genres_value_id = Column(Integer, ForeignKey('value_id.id'),
                             nullable=False)

    av_work = relationship('AVWork', foreign_keys=[av_work_id])
    country = relationship('ValueID', foreign_keys=[country_value_id])
    genres = relationship('ValueID', foreign_keys=[genres_value_id])


class Episode(Base):
    __tablename__ = 'episode'

    id = Column(Integer, Sequence('episode_id_seq'), primary_key=True)

    external_object_id = Column(Integer, ForeignKey('external_object.id'),
                                nullable=False)
    season_id = Column(Integer, ForeignKey('season.id'), nullable=False)

    external_object = relationship('ExternalObject',
                                   foreign_keys=[external_object_id])
    season = relationship('Season', foreign_keys=[season_id])
    number = Column(Integer, nullable=False)


class Season(Base):
    __tablename__ = 'season'

    id = Column(Integer, Sequence('season_id_seq'), primary_key=True)

    external_object_id = Column(Integer, ForeignKey('external_object.id'),
                                nullable=False)
    serie_id = Column(Integer, ForeignKey('serie.id'), nullable=False)

    external_object = relationship('ExternalObject',
                                   foreign_keys=[external_object_id])
    serie = relationship('serie', foreign_keys=[serie_id])
    number = Column(Integer, nullable=False)


class Serie(Base):
    __tablename__ = 'serie'
    id = Column(Integer, Sequence('serie_id_seq'), primary_key=True)

    external_object_id = Column(Integer, ForeignKey('external_object.id'),
                                nullable=False)
    title_value_id = Column(Integer, ForeignKey('value_id.id'),
                            nullable=False)
    country_value_id = Column(Integer, ForeignKey('value_id.id'),
                              nullable=False)
    genres_value_id = Column(Integer, ForeignKey('value_id.id'),
                             nullable=False)

    external_object = relationship('ExternalObject',
                                   foreign_keys=[external_object_id])
    title = relationship('ValueID', foreign_keys=[title_value_id])
    country = relationship('ValueID', foreign_keys=[country_value_id])
    genres = relationship('ValueID', foreign_keys=[genres_value_id])
