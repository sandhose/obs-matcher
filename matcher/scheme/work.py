import enum
from .mixins import ExternalObjectMixin
from .object import ExternalObjectType
from matcher import db


class AVWorkType(enum.Enum):
    MOVIE = 1
    EPISODE = 2

    def model(self):
        if (self == AVWork.MOVIE):
            return Movie
        else:
            return Episode


class AVWork(db.Model, ExternalObjectMixin(ExternalObjectType.AV_WORK)):
    __tablename__ = 'av_work'

    id = db.Column(db.Integer,
                   db.Sequence('av_work_id_seq'),
                   primary_key=True)

    title_value_id = db.Column(db.Integer,
                               db.ForeignKey('value_id.id'),
                               nullable=False)
    date_value_id = db.Column(db.Integer,
                              db.ForeignKey('value_id.id'),
                              nullable=False)
    duration_value_id = db.Column(db.Integer,
                                  db.ForeignKey('value_id.id'),
                                  nullable=False)

    title = db.relationship('ValueID',
                            foreign_keys=[title_value_id])
    date = db.relationship('ValueID',
                           foreign_keys=[date_value_id])
    type = db.Column(db.Enum(AVWorkType, name='avwork_type'),
                     nullable=False)
    duration = db.relationship('ValueID',
                               foreign_keys=[duration_value_id])
    roles = db.relationship('Role',
                            back_populates='av_work')

    @property
    def work(self):
        return object_session(self).\
               query(self.type.model()).\
               filter(self.type.model().av_work_id == self.id).\
               first()

    def __repr__(self):
        return '<AVWork {} {}>'.format(self.type, self.title)


class Movie(db.Model, ExternalObjectMixin(ExternalObjectType.MOVIE)):
    __tablename__ = 'movie'

    id = db.Column(db.Integer,
                   db.Sequence('movie_id_seq'),
                   primary_key=True)
    av_work_id = db.Column(db.Integer,
                           db.ForeignKey('av_work.id'),
                           nullable=False)
    country_value_id = db.Column(db.Integer,
                                 db.ForeignKey('value_id.id'),
                                 nullable=False)
    genres_value_id = db.Column(db.Integer,
                                db.ForeignKey('value_id.id'),
                                nullable=False)

    av_work = db.relationship('AVWork',
                              foreign_keys=[av_work_id])
    country = db.relationship('ValueID',
                              foreign_keys=[country_value_id])
    genres = db.relationship('ValueID',
                             foreign_keys=[genres_value_id])

    def __repr__(self):
        return '<Movie {}>'.format(self.av_work)


class Episode(db.Model, ExternalObjectMixin(ExternalObjectType.EPISODE)):
    __tablename__ = 'episode'

    id = db.Column(db.Integer,
                   db.Sequence('episode_id_seq'),
                   primary_key=True)

    av_work_id = db.Column(db.Integer,
                           db.ForeignKey('av_work.id'),
                           nullable=False)

    season_id = db.Column(db.Integer,
                          db.ForeignKey('season.id'),
                          nullable=False)

    av_work = db.relationship('AVWork',
                              foreign_keys=[av_work_id])
    season = db.relationship('Season',
                             foreign_keys=[season_id])
    number = db.Column(db.Integer,
                       nullable=False)

    def __repr__(self):
        return '<Episode {} {} {}>'.format(self.number, self.av_work,
                                           self.season)


class Season(db.Model, ExternalObjectMixin(ExternalObjectType.SEASON)):
    __tablename__ = 'season'

    id = db.Column(db.Integer,
                   db.Sequence('season_id_seq'),
                   primary_key=True)

    serie_id = db.Column(db.Integer,
                         db.ForeignKey('serie.id'), nullable=False)

    serie = db.relationship('Serie', foreign_keys=[serie_id])
    number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return '<Season {} {}>'.format(self.number, self.serie)


class Serie(db.Model, ExternalObjectMixin(ExternalObjectType.SERIE)):
    __tablename__ = 'serie'
    id = db.Column(db.Integer,
                   db.Sequence('serie_id_seq'),
                   primary_key=True)

    title_value_id = db.Column(db.Integer,
                               db.ForeignKey('value_id.id'),
                               nullable=False)
    country_value_id = db.Column(db.Integer,
                                 db.ForeignKey('value_id.id'),
                                 nullable=False)
    genres_value_id = db.Column(db.Integer,
                                db.ForeignKey('value_id.id'),
                                nullable=False)

    title = db.relationship('ValueID',
                            foreign_keys=[title_value_id])
    country = db.relationship('ValueID',
                              foreign_keys=[country_value_id])
    genres = db.relationship('ValueID',
                             foreign_keys=[genres_value_id])

    def __repr__(self):
        return '<Serie {}>'.format(self.title)
